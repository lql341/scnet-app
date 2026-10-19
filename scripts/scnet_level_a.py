#!/usr/bin/env python3
"""Execute the local, package-level SCNet level-A standard suite.

This runner validates packaging behavior only. It does not submit a job and
cannot certify a device. Applications may expose two deterministic negative
test modes through ``SCNET_LEVEL_A_FORCE_FAILURE=1`` and
``SCNET_LEVEL_A_BAD_INPUT=1``; hooks that do not implement those modes fail
the corresponding checks instead of being treated as implicitly compliant.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Union


CHECK_IDS = (
    "entrypoint",
    "exit_status",
    "bad_input",
    "environment",
    "device_evidence",
    "offline",
    "relocatable",
    "idempotent",
)

_TEXT_SUFFIXES = {".bash", ".csh", ".ksh", ".lua", ".pl", ".py", ".rb", ".sh", ".tcl"}
_NETWORK_PATTERNS = (
    r"\bcurl\b",
    r"\bwget\b",
    r"\bgit\s+clone\b",
    r"\b(?:pip|pip3)\s+install\b",
    r"\bconda\s+install\b",
    r"\b(?:apt|dnf|yum)\s+(?:install|update)\b",
    r"\b(?:ssh|scp)\b",
    r"https?://",
    r"\b(?:requests|urllib|socket)\b",
)


def _load_app(root: Path) -> dict:
    try:
        value = json.loads((root / "app.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("cannot read app.json: " + str(exc)) from exc
    if not isinstance(value, dict):
        raise ValueError("app.json must contain an object")
    for key in ("name", "target", "run", "check", "validation"):
        if key not in value:
            raise ValueError("app.json missing " + key)
    return value


def _safe_relative(value: str) -> Path:
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
        raise ValueError("expected a relative path: " + value)
    return path


def _copy_fixture(root: Path, destination: Path) -> None:
    def ignore(path: str, names: List[str]) -> set:
        return {name for name in names if name in {".git", ".private", "__pycache__"}}

    shutil.copytree(root, destination, ignore=ignore)


def _run_hook(root: Path, env_overrides: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
    app = _load_app(root)
    run = _safe_relative(app["run"])
    env = os.environ.copy()
    env.update(env_overrides or {})
    env["SCNET_LEVEL_A_ROOT"] = str(root)
    return subprocess.run(
        ["bash", str(run)],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        timeout=120,
    )


def _run_env(root: Path) -> subprocess.CompletedProcess[str]:
    env_script = root / "runtime/scripts/env.sh"
    if not env_script.is_file() or env_script.is_symlink():
        raise ValueError("runtime/scripts/env.sh is missing or linked")
    return subprocess.run(
        ["bash", "-c", "set -euo pipefail; source runtime/scripts/env.sh; env"],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=30,
    )


def _runtime_text_files(root: Path) -> list[Path]:
    runtime = root / "runtime"
    if not runtime.is_dir():
        return []
    return [
        path for path in sorted(runtime.rglob("*"))
        if path.is_file() and not path.is_symlink() and path.suffix.lower() in _TEXT_SUFFIXES
    ]


def _hash_files(paths: list[Path], root: Path) -> dict[str, str]:
    result = {}
    for path in paths:
        result[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _post_install(root: Path) -> subprocess.CompletedProcess[str] | None:
    post = root / "runtime/scripts/post.sh"
    if not post.exists():
        return None
    if post.is_symlink() or not post.is_file():
        raise ValueError("runtime/scripts/post.sh is missing or linked")
    return subprocess.run(["bash", str(post)], cwd=root, text=True, capture_output=True, timeout=30)


def _row(check_id: str, status: str, detail: str = "") -> dict:
    value = {"id": check_id, "status": status}
    if detail:
        value["detail"] = detail
    return value


def _check_entrypoint(root: Path) -> dict:
    proc = _run_hook(root)
    results = root / "results"
    if proc.returncode != 0:
        return _row("entrypoint", "failed", "run hook exited %d: %s" % (proc.returncode, proc.stderr.strip()[:400]))
    if not results.is_dir() or not any(path.is_file() for path in results.rglob("*")):
        return _row("entrypoint", "failed", "run hook did not write a non-empty results directory")
    return _row("entrypoint", "passed")


def _check_negative(root: Path, check_id: str, variable: str) -> dict:
    proc = _run_hook(root, {variable: "1"})
    if proc.returncode == 0:
        return _row(check_id, "failed", "run hook ignored " + variable)
    if not proc.stderr.strip() and not proc.stdout.strip():
        return _row(check_id, "failed", "negative run produced no diagnostic output")
    return _row(check_id, "passed")


def _check_environment(root: Path) -> dict:
    try:
        proc = _run_env(root)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return _row("environment", "failed", str(exc))
    if proc.returncode:
        return _row("environment", "failed", proc.stderr.strip()[:400] or "env.sh exited nonzero")
    return _row("environment", "passed")


def _check_device_evidence(root: Path, app: dict) -> dict:
    declaration = app.get("validation", {}).get("device_evidence")
    if app.get("target") != "hygon-z100" and not declaration:
        return _row("device_evidence", "not_applicable", "CPU target has no device evidence requirement")
    if not declaration:
        return _row("device_evidence", "failed", "accelerator target requires validation.device_evidence")
    try:
        artifact = _safe_relative(declaration["artifact"])
        patterns = declaration["patterns"]
        if not patterns:
            raise ValueError("device evidence patterns are empty")
        path = root / "results" / artifact
        text = path.read_text(encoding="utf-8")
        missing = [pattern for pattern in patterns if re.search(pattern, text, re.MULTILINE) is None]
        if missing:
            return _row("device_evidence", "failed", "patterns not found: " + ", ".join(missing))
    except (KeyError, OSError, ValueError, re.error) as exc:
        return _row("device_evidence", "failed", str(exc))
    return _row("device_evidence", "passed")


def _check_offline(root: Path) -> dict:
    findings = []
    for path in _runtime_text_files(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in _NETWORK_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                findings.append(path.relative_to(root).as_posix() + ": " + pattern)
    if findings:
        return _row("offline", "failed", "network/install command found: " + "; ".join(findings[:4]))
    return _row("offline", "passed")


def _check_relocation(root: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="scnet-level-a-relocated-") as tmp:
        relocated = Path(tmp) / "package"
        _copy_fixture(root, relocated)
        try:
            first = _post_install(relocated)
            if first is not None and first.returncode:
                return _row("relocatable", "failed", first.stderr.strip()[:400] or "post.sh exited nonzero")
            _run_env(relocated)
            proc = _run_hook(relocated)
            if proc.returncode:
                return _row("relocatable", "failed", proc.stderr.strip()[:400] or "relocated run failed")
            original = str(root)
            leaked = [path.relative_to(relocated).as_posix() for path in _runtime_text_files(relocated)
                      if original in path.read_text(encoding="utf-8", errors="replace")]
            if leaked:
                return _row("relocatable", "failed", "original path remains in: " + ", ".join(leaked[:4]))
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            return _row("relocatable", "failed", str(exc))
    return _row("relocatable", "passed")


def _check_idempotent(root: Path) -> dict:
    paths = _runtime_text_files(root)
    before = _hash_files(paths, root)
    try:
        first = _post_install(root)
        if first is not None and first.returncode:
            return _row("idempotent", "failed", first.stderr.strip()[:400] or "first post.sh run failed")
        after_first = _hash_files(_runtime_text_files(root), root)
        second = _post_install(root)
        if second is not None and second.returncode:
            return _row("idempotent", "failed", second.stderr.strip()[:400] or "second post.sh run failed")
        after_second = _hash_files(_runtime_text_files(root), root)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return _row("idempotent", "failed", str(exc))
    if before != after_first and after_first != after_second:
        return _row("idempotent", "failed", "post-install output changes on every invocation")
    return _row("idempotent", "passed")


def run(root: Union[str, Path], output: Optional[Union[str, Path]] = None) -> dict:
    """Run all eight checks and optionally write a JSON evidence file."""
    source = Path(root).resolve()
    app = _load_app(source)
    with tempfile.TemporaryDirectory(prefix="scnet-level-a-") as tmp:
        fixture = Path(tmp) / "fixture"
        _copy_fixture(source, fixture)
        checks = [
            _check_entrypoint(fixture),
            _check_negative(fixture, "exit_status", "SCNET_LEVEL_A_FORCE_FAILURE"),
            _check_negative(fixture, "bad_input", "SCNET_LEVEL_A_BAD_INPUT"),
            _check_environment(fixture),
            _check_device_evidence(fixture, app),
            _check_offline(fixture),
            _check_relocation(fixture),
            _check_idempotent(fixture),
        ]
    passed = all(item["status"] in ("passed", "not_applicable") for item in checks)
    result = {
        "standard": "level-a-v1",
        "application": app["name"],
        "target": app["target"],
        "passed": passed,
        "checks": checks,
    }
    if output is not None:
        destination = Path(output).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("application", type=Path)
    parser.add_argument("--output", type=Path, help="write structured level-A evidence JSON")
    args = parser.parse_args(argv)
    try:
        result = run(args.application, args.output)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print("scnet-level-a: " + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
