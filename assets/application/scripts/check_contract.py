#!/usr/bin/env python3
"""Check the generated application's first-use contract artifacts.

This is intentionally separate from check.py: check.py owns numerical or
functional correctness, while this script only checks onboarding structure.
"""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = (
    "references/first-use.md",
    "scripts/doctor.py",
    "tests/test_first_use.py",
)


def main():
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        print("missing first-use contract files: " + ", ".join(missing), file=sys.stderr)
        return 2
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/doctor.py"), "--json"],
        text=True,
        capture_output=True,
    )
    if completed.returncode not in (0, 2):
        print("doctor failed: " + (completed.stderr or completed.stdout), file=sys.stderr)
        return 1
    try:
        status = json.loads(completed.stdout)
    except ValueError:
        print("doctor did not emit JSON", file=sys.stderr)
        return 1
    required = {
        "schema_version",
        "credentials",
        "configuration",
        "readiness",
        "openapi_ready",
        "next_steps",
    }
    if not required.issubset(status):
        print("doctor JSON is missing contract fields", file=sys.stderr)
        return 1
    print("first-use contract files and doctor JSON are present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
