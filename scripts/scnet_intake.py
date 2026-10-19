#!/usr/bin/env python3
"""Inspect a source archive, source tree, installed tree, or existing skill."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import zipfile


BUILD_MARKERS = (
    "CMakeLists.txt", "Makefile", "makefile", "configure",
    "Allwmake", "Allwmake-modules", "pyproject.toml", "setup.py",
    "go.mod", "Cargo.toml",
)
LICENSE_MARKERS = ("LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING", "NOTICE")
ARCHIVE_SUFFIXES = (".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz", ".zip")


def _hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_symlink() or not path.is_file() or ".git" in relative.parts:
            continue
        name = relative.as_posix().encode("utf-8")
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        data = path.read_bytes()
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def _safe_member(name: str) -> Path:
    path = Path(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name or "\x00" in name:
        raise ValueError("archive contains an unsafe path: " + name)
    return path


def _extract_archive(source: Path, destination: Path) -> None:
    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as archive:
            for member in archive.infolist():
                relative = _safe_member(member.filename)
                target = destination / relative
                if member.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as stream, target.open("wb") as output:
                    shutil.copyfileobj(stream, output)
        return
    with tarfile.open(source, "r:*") as archive:
        for member in archive.getmembers():
            relative = _safe_member(member.name)
            if member.issym() or member.islnk() or member.isdev():
                raise ValueError("archive contains a link or device entry: " + member.name)
            target = destination / relative
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as stream, target.open("wb") as output:
                if stream is not None:
                    shutil.copyfileobj(stream, output)


def _workspace_root(root: Path) -> Path:
    entries = [path for path in root.iterdir() if path.name != "__MACOSX"]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return root


def _classify(root: Path) -> tuple[str, str]:
    if (root / "SKILL.md").is_file() and ((root / "app.json").is_file() or (root / "VERSION").is_file()):
        return "skill", "existing skill repository"
    if any((root / marker).is_file() for marker in BUILD_MARKERS):
        return "source", "build metadata detected"
    if any((root / name).is_dir() for name in ("bin", "lib", "lib64")):
        return "installed", "installation layout detected"
    return "unknown", "no supported build or installation marker detected"


def inspect(source: str | Path, output: str | Path | None = None) -> dict:
    source = Path(source).expanduser().resolve()
    if not source.exists() or source.is_symlink():
        raise ValueError("input does not exist or is a symlink: " + str(source))
    temporary = None
    if source.is_file():
        if source.suffix.lower() not in ARCHIVE_SUFFIXES and not source.name.lower().endswith((".tar.gz", ".tar.bz2", ".tar.xz")):
            raise ValueError("input file is not a supported source archive")
        temporary = tempfile.TemporaryDirectory(prefix="scnet-intake-")
        extracted = Path(temporary.name)
        try:
            _extract_archive(source, extracted)
        except Exception:
            temporary.cleanup()
            raise
        root = _workspace_root(extracted)
        input_kind = "archive"
    elif source.is_dir():
        root = source
        input_kind = "directory"
    else:
        raise ValueError("input must be a directory or supported archive")
    kind, reason = _classify(root)
    files = [path for path in root.rglob("*") if path.is_file() and not path.is_symlink()]
    markers = [marker for marker in BUILD_MARKERS if (root / marker).is_file()]
    adapter = "openfoam-allwmake" if "Allwmake" in markers else (
        "cmake-or-make" if kind == "source" else None
    )
    next_step = {
        "source": "run quick-build or a source-specific adapter",
        "installed": "inspect bin/lib layout and author an installation-backed skill",
        "skill": "validate the existing skill and review its evidence",
        "unknown": "request build instructions or a representative executable",
    }[kind]
    if adapter == "openfoam-allwmake":
        next_step = "use the OpenFOAM Allwmake adapter; ThirdParty and site toolchain must be resolved first"
    result = {
        "intake_version": 1,
        "input": str(source),
        "input_kind": input_kind,
        "workspace_root": str(root),
        "classification": kind,
        "classification_reason": reason,
        "file_count": len(files),
        "source_sha256": _hash_tree(root),
        "build_markers": markers,
        "adapter_hint": adapter,
        "license_files": [name for name in LICENSE_MARKERS if (root / name).is_file()],
        "next": next_step,
    }
    if output is not None:
        destination = Path(output).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    if temporary is not None:
        temporary.cleanup()
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(inspect(args.source, args.output), indent=2, ensure_ascii=True))
        return 0
    except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as exc:
        print("scnet-intake: " + str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
