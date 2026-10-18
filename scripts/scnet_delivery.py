"""Offline delivery gate for the SCNet software package and agent skill."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import tarfile

import scnet_evidence as evidence


def _file(root, name):
    path = root / name
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        raise ValueError("delivery file escapes package: " + name) from None
    if path.is_symlink() or not path.is_file():
        raise ValueError("missing, linked or escaping delivery file: " + name)
    return path


def _files(root, directory):
    base = root / directory
    if base.is_symlink() or not base.is_dir():
        return []
    result = []
    for path in sorted(base.rglob("*")):
        if path.is_symlink():
            raise ValueError("runtime package contains a symlink: " + str(path))
        if path.is_file():
            result.append(path)
    return result


def _configuration(root):
    path = _file(root, "delivery.json")
    data = evidence.read_object(path)
    if set(data) != {"standard_level", "package_name", "max_attempts", "runtime_evidence"}:
        raise ValueError("delivery.json requires standard_level, package_name, max_attempts and runtime_evidence")
    if data["standard_level"] != "A":
        raise ValueError("this success gate currently implements only SCNet packaging level A")
    if type(data["max_attempts"]) is not int or not 1 <= data["max_attempts"] <= 100:
        raise ValueError("max_attempts must be an integer from 1 to 100")
    name = data["package_name"]
    match = re.fullmatch(r"([a-z0-9_]{1,20})-([0-9][0-9.]{0,19})-([a-z0-9_][a-z0-9_.]{0,49})\.tar", name) if isinstance(name, str) else None
    if not match or match.group(2).endswith(".") or ".." in match.group(2) or not match.group(3)[0].isalnum() or not match.group(3)[-1].isalnum():
        raise ValueError("package_name must follow the official X-Y-Z.tar naming rules")
    runtime = data["runtime_evidence"]
    if not isinstance(runtime, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._/-]{0,127}", runtime) or ".." in Path(runtime).parts:
        raise ValueError("runtime_evidence must be a relative result file")
    return data


def attempt_blocks(root):
    root = Path(root).resolve()
    if not (root / "delivery.json").is_file():
        return []
    config = _configuration(root)
    count = len(list((root / ".private/evidence").glob("*/record.json")))
    return ["Recorded test attempt limit reached; stop or obtain a revised authorized limit."] if count >= config["max_attempts"] else []


def gate(root, app, binding, verification, implementation_ready, deployment_blocks):
    root = Path(root).resolve()
    config = _configuration(root)
    failures = []
    if not implementation_ready:
        failures.append("implement run/check hooks and independent acceptance checks")
    failures.extend(deployment_blocks)
    required_docs = ("SKILL.md", "README.md", "README_CN.md", "references/validation.md", "references/validation_CN.md", "tests/README.md")
    for name in required_docs:
        try:
            text = _file(root, name).read_text(encoding="utf-8")
            if not text.strip() or any(marker in text for marker in ("__APP_NAME__", "Status: **unverified**", "状态：**未验证**", "Status: scaffold", "状态：脚手架")):
                failures.append("complete delivery documentation: " + name)
        except (OSError, ValueError):
            failures.append("add delivery documentation: " + name)
    runtime = root / "runtime"
    for directory in ("app", "case", "scripts"):
        if not _files(runtime, directory):
            failures.append("populate official runtime/" + directory + "/ directory")
    if not _files(runtime, "app/bin"):
        failures.append("include an application executable in runtime/app/bin/")
    runtime_files = [path for directory in ("app", "case", "scripts", "source") for path in _files(runtime, directory)]
    staged = set(app["files"])
    unstaged = [path.relative_to(root).as_posix() for path in runtime_files if path.relative_to(root).as_posix() not in staged]
    if unstaged:
        failures.append("stage all runtime package files in app.json files: " + ", ".join(unstaged[:5]))
    if not _files(runtime, "case/testcase"):
        failures.append("include a runnable level-A test case")
    for name in ("case/.check", "scripts/env.sh"):
        try:
            if not _file(runtime, name).stat().st_size:
                failures.append("complete runtime/" + name)
        except (OSError, ValueError):
            failures.append("add runtime/" + name)
    if not list((runtime / "case").glob("*.slurm")):
        failures.append("add a site-adjusted Slurm example in runtime/case/")
    attempts = sorted((root / ".private/evidence").glob("*/record.json"))
    if len(attempts) > config["max_attempts"]:
        failures.append("recorded attempts exceed the configured maximum")
    if verification["verification"]["correctness"] != "passed":
        failures.append("latest current acceptance record must pass")
    if verification["verification"]["scheduler"] != "passed":
        failures.append("check the matching SCNet job and successful scheduler history")
    run_id = verification["verification"]["run_id"]
    if run_id:
        try:
            record = evidence.read_object(root / ".private/evidence" / run_id / "record.json")
            artifact_root = root / ".private/evidence" / run_id / "artifacts"
            runtime_path = evidence.safe_file(artifact_root, config["runtime_evidence"])
            if config["runtime_evidence"] not in record["result_hashes"] or hashlib.sha256(runtime_path.read_bytes()).hexdigest() != record["result_hashes"][config["runtime_evidence"]]:
                raise ValueError("runtime evidence not recorded")
            observed = evidence.read_object(runtime_path)
            if observed.get("target") != app["target"] or observed.get("device_used") is not True or not observed.get("runtime") or not observed.get("device"):
                raise ValueError("runtime evidence lacks target, actual device or runtime")
        except (OSError, ValueError, KeyError, TypeError):
            failures.append("record target-matched runtime/device evidence from the accepted job")
    else:
        failures.append("record a completed test case")
    remaining = max(0, config["max_attempts"] - len(attempts))
    return {"application": app["name"], "standard_level": "A", "package_name": config["package_name"],
            "ready_to_build": not failures, "blocked_by": failures, "attempts_recorded": len(attempts),
            "attempts_remaining": remaining, "retry_allowed": bool(failures and remaining),
            "verification": verification["verification"],
            "meaning": "Passes the declared delivery gate; hardware certification requires independent review."}


def build(root, app, gate_result, output):
    if not gate_result["ready_to_build"]:
        raise ValueError("delivery gate failed: " + "; ".join(gate_result["blocked_by"]))
    root = Path(root).resolve()
    output = Path(output).resolve()
    if output.exists():
        raise ValueError("output directory already exists; choose a fresh path")
    if output == root or root in output.parents:
        raise ValueError("output must be outside the source application")
    runtime = root / "runtime"
    payload = []
    for directory in ("app", "case", "scripts", "source"):
        payload.extend(_files(runtime, directory))
    output.mkdir(parents=True, exist_ok=False)
    package = output / gate_result["package_name"]
    with tarfile.open(package, "w", format=tarfile.PAX_FORMAT) as archive:
        for path in payload:
            archive.add(path, arcname=path.relative_to(runtime).as_posix(), recursive=False)
    skill = output / app["name"]
    skill.mkdir()
    selected = ["SKILL.md", "app.json", "README.md", "README_CN.md", "VERSION", "LICENSE", "delivery.json"]
    for directory in ("agents", "scripts", "references", "tests", "runtime"):
        selected.extend(p.relative_to(root).as_posix() for p in _files(root, directory))
    import shutil
    for name in selected:
        source = _file(root, name)
        target = skill / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    manifest = {"application": app["name"], "standard_level": gate_result["standard_level"],
                "runtime_tar": package.name, "skill_directory": skill.name,
                "files": {path.relative_to(output).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in sorted(output.rglob("*")) if path.is_file()}}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"delivery": str(output), "runtime_tar": str(package), "skill": str(skill), "manifest": str(output / "manifest.json")}
