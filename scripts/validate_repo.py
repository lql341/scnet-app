#!/usr/bin/env python3
"""Offline repository/asset validation; no network or compute allocation."""
import ast
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import scnet_app

ROOT = Path(__file__).resolve().parent.parent
PRIVATE_PATTERNS = (
    re.compile(r"/home/[A-Za-z0-9._-]+"),
    re.compile("/public" + "/home/"),
    re.compile(r"/work/home/"),
    re.compile(r"\b1[0-9]{8}\b"),
    re.compile(r"BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY"),
    re.compile(r"(?i)(SECRET_KEY|ACCESS_KEY|PASSWORD)\s*=\s*[^<\s]" ),
)


def check_private_material():
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if relative == Path("scripts/validate_repo.py"):
            continue
        if any(part in (".git", "_deps", "__pycache__") for part in relative.parts):
            continue
        if not path.is_file() or path.suffix in (".png", ".jpg", ".jpeg", ".gif", ".pdf", ".gz", ".zip", ".tar", ".pyc"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in PRIVATE_PATTERNS:
            match = pattern.search(text)
            if match:
                raise ValueError(
                    "possible private material in {}: {}".format(relative, match.group(0))
                )


def main():
    check_private_material()
    version = (ROOT / "VERSION").read_text().strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("invalid VERSION")
    for name in ("README.md", "README_CN.md", "CHANGELOG.md"):
        if version not in (ROOT / name).read_text(encoding="utf-8"):
            raise ValueError("release version missing in " + name)
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in (".git", "_deps", "__pycache__") for part in relative.parts) or not path.is_file():
            continue
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 8))
        if path.suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
        if path.suffix == ".sh" and b"\r" in path.read_bytes():
            raise ValueError("CRLF is unsafe for remote Bash: " + str(relative))
        if path.suffix == ".md":
            for link in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
                if "://" not in link and not link.startswith("#") and not (path.parent / link.split("#")[0]).exists():
                    raise ValueError("broken Markdown link: " + str(relative) + " -> " + link)
    matrix = json.loads((ROOT / "stacks/matrix.json").read_text(encoding="utf-8"))
    ids = [item.get("id") for item in matrix.get("signatures", [])]
    if len(ids) != len(set(ids)) or any(not item for item in ids):
        raise ValueError("stack matrix ids must be unique and non-empty")
    index = json.loads((ROOT / "stacks/release-index.json").read_text(encoding="utf-8"))
    entries = index.get("entries") or []
    if (index.get("components") or {}).get("scnet-app") != version:
        raise ValueError("release index scnet-app version does not match VERSION")
    names = [item.get("application") for item in entries]
    if index.get("schema_version") != 1 or len(names) != len(set(names)) or not all(names):
        raise ValueError("release index must have unique application names")
    required = {
        "application",
        "skill_version",
        "adapter",
        "adapter_commit",
        "scnet_hpc_min",
        "scnet_hpc_tested",
        "runtime",
        "target",
        "module",
        "validated_scope",
        "unverified",
    }
    for item in entries:
        if not required.issubset(item):
            raise ValueError("release index entry is missing fields: " + str(item.get("application")))
        if not item["validated_scope"] or not item["unverified"]:
            raise ValueError("release index must state validated and unverified scope")
    for relative in (
        "references/first-use.md",
        "scripts/doctor.py",
        "scripts/check_contract.py",
        "tests/test_first_use.py",
    ):
        if not (ROOT / "assets" / "application" / relative).is_file():
            raise ValueError("application template is missing " + relative)
    standard = json.loads((ROOT / "standards/level-a-v1.json").read_text(encoding="utf-8"))
    if standard.get("level") != "A" or len(standard.get("checks", [])) != 8:
        raise ValueError("level-a-v1 must define exactly eight standard checks")
    with tempfile.TemporaryDirectory() as tmp:
        destination = Path(tmp) / "scnet-smoke"
        scnet_app.init_app("scnet-smoke", destination, "https://example.org/science", "hygon-z100")
        scnet_app.load_app(destination)
        for path in destination.rglob("*"):
            if path.is_file() and b"__APP_NAME__" in path.read_bytes():
                raise ValueError("unexpanded application template")
        completed = subprocess.run(
            [sys.executable, str(destination / "scripts/check_contract.py")],
            text=True,
            capture_output=True,
        )
        if completed.returncode != 0:
            raise ValueError(
                "generated first-use contract check failed: "
                + (completed.stderr or completed.stdout).strip()
            )
        tests = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            cwd=destination,
            text=True,
            capture_output=True,
        )
        if tests.returncode != 0:
            raise ValueError(
                "generated first-use tests failed: "
                + (tests.stderr or tests.stdout).strip()
            )
    print("Repository and generated package validation passed; compute remains unverified.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
