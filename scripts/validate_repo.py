#!/usr/bin/env python3
"""Offline repository/asset validation; no network or compute allocation."""
import ast
import json
from pathlib import Path
import re
import sys
import tempfile

import scnet_app

ROOT = Path(__file__).resolve().parent.parent


def main():
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
    with tempfile.TemporaryDirectory() as tmp:
        destination = Path(tmp) / "scnet-smoke"
        scnet_app.init_app("scnet-smoke", destination, "https://example.org/science", "hygon-z100")
        scnet_app.load_app(destination)
        for path in destination.rglob("*"):
            if path.is_file() and b"__APP_NAME__" in path.read_bytes():
                raise ValueError("unexpanded application template")
    print("Repository and generated package validation passed; compute remains unverified.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
