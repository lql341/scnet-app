#!/usr/bin/env python3
"""Build a small CPU project into a runnable local SCNet skill package."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
from typing import Optional


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import scnet_app
from scnet_platform import find_bash, is_executable


def source_sha256(source: Path) -> str:
    digest = hashlib.sha256()
    ignored = {".git", "build", "_build", "__pycache__"}
    for path in sorted(source.rglob("*")):
        if not path.is_file() or any(part in ignored for part in path.relative_to(source).parts):
            continue
        relative = path.relative_to(source).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(path.read_bytes())
    return digest.hexdigest()


def detect_build_system(source: Path) -> str:
    if (source / "CMakeLists.txt").is_file():
        return "cmake"
    if (source / "Makefile").is_file() or (source / "makefile").is_file():
        return "make"
    raise ValueError("source must contain CMakeLists.txt or Makefile")


def find_binary(root: Path, requested: Optional[str]) -> Path:
    if requested:
        path = root / requested
        if os.name == "nt" and not path.exists() and not path.suffix:
            path = path.with_suffix(".exe")
        if not path.is_file() or not is_executable(path):
            raise ValueError("built executable not found: " + requested)
        return path
    candidates = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or not is_executable(path):
            continue
        relative = path.relative_to(root)
        if any(part in {"CMakeFiles", ".git", "__pycache__"} for part in relative.parts):
            continue
        if path.suffix in {".so", ".dylib", ".dll"}:
            continue
        candidates.append(path)
    if len(candidates) != 1:
        names = ", ".join(path.relative_to(root).as_posix() for path in candidates[:8])
        raise ValueError("expected one built executable; found %d%s" % (
            len(candidates), (": " + names) if names else ""))
    return candidates[0]


def _write(path: Path, text: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
    if executable:
        path.chmod(path.stat().st_mode | 0o111)


def write_runtime(destination: Path, binary_name: str, smoke_input: str, expected: str) -> None:
    runtime = destination / "runtime"
    _write(runtime / "case/testcase/input.txt", smoke_input)
    _write(runtime / "case/.check", expected)
    _write(runtime / "case/cpu.slurm",
           "#!/usr/bin/env bash\nset -euo pipefail\nbash scripts/run.sh\n", True)
    _write(runtime / "scripts/env.sh",
           "#!/usr/bin/env bash\nexport PATH=\"$PWD/app/bin:$PATH\"\n", True)
    _write(destination / "scripts/run.sh", """#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ "${SCNET_LEVEL_A_FORCE_FAILURE:-0}" = 1 ]; then
  echo "forced failure requested" >&2
  exit 9
fi
if [ "${SCNET_LEVEL_A_BAD_INPUT:-0}" = 1 ] || [ ! -s "$ROOT/runtime/case/testcase/input.txt" ]; then
  echo "missing or empty smoke input" >&2
  exit 2
fi
mkdir -p "$ROOT/results"
"$ROOT/runtime/app/bin/%s" < "$ROOT/runtime/case/testcase/input.txt" > "$ROOT/results/output.txt"
printf '%%s\n' '{"target":"hygon-c86","device_used":false,"device":"host-cpu","runtime":"host-cpu"}' > "$ROOT/results/runtime.json"
""" % binary_name, True)
    _write(destination / "scripts/check.py", """#!/usr/bin/env python3
import json
from pathlib import Path
import sys

results = Path(sys.argv[1]) if len(sys.argv) == 2 else Path("results")
root = results.parent
try:
    expected = (root / "runtime/case/.check").read_text(encoding="utf-8")
    observed = (results / "output.txt").read_text(encoding="utf-8")
    runtime = json.loads((results / "runtime.json").read_text(encoding="utf-8"))
except (OSError, ValueError) as exc:
    print("checker: " + str(exc), file=sys.stderr)
    raise SystemExit(1)
passed = observed == expected and runtime.get("target") == "hygon-c86" and runtime.get("device_used") is False
print(json.dumps({"checks": {"smoke": passed}, "observed_output": observed, "runtime": runtime}))
raise SystemExit(0 if passed else 1)
""", True)


def write_runtime_tar(destination: Path, package_name: str) -> Path:
    package = destination / package_name
    with tarfile.open(package, "w", format=tarfile.PAX_FORMAT) as archive:
        for directory in ("app", "case", "scripts"):
            for path in sorted((destination / "runtime" / directory).rglob("*")):
                if path.is_file():
                    archive.add(path, arcname=path.relative_to(destination / "runtime").as_posix(),
                               recursive=False)
    return package


def build(source: Path, output: Path, name: str, upstream: str, smoke_input: str,
          expected: str, binary: str | None = None) -> dict:
    source = source.resolve()
    output = output.resolve()
    if not source.is_dir():
        raise ValueError("source directory does not exist: " + str(source))
    if output.exists():
        raise ValueError("destination already exists; no files were overwritten")
    build_system = detect_build_system(source)
    digest = source_sha256(source)
    with tempfile.TemporaryDirectory(prefix="scnet-quick-build-") as temp_name:
        temp = Path(temp_name)
        staged = temp / "source"
        shutil.copytree(source, staged)
        build_root = temp / "build"
        if build_system == "cmake":
            subprocess.run(["cmake", "-S", str(staged), "-B", str(build_root),
                            "-DCMAKE_BUILD_TYPE=Release"], check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["cmake", "--build", str(build_root), "--config", "Release"],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            artifact_root = build_root
        else:
            subprocess.run(["make", "-C", str(staged)], check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            artifact_root = staged
        built = find_binary(artifact_root, binary)
        binary_name = built.name
        scnet_app.init_app(name, output, upstream, "hygon-c86")
        destination = output
        (destination / "runtime/app/bin").mkdir(parents=True, exist_ok=True)
        shutil.copy2(built, destination / "runtime/app/bin" / binary_name)

    write_runtime(destination, binary_name, smoke_input, expected)
    app_data = json.loads((destination / "app.json").read_text(encoding="utf-8"))
    app_data["acceptance"] = "Packaged CPU smoke output must exactly match runtime/case/.check."
    app_data["checks"] = [{"name": "smoke", "kind": "hook", "required": True,
                           "criterion": "Run the packaged CPU executable and compare output exactly."}]
    app_data["provenance"] = {"revision": digest, "license": "See upstream source license."}
    app_data["files"] = [
        "runtime/app/bin/" + binary_name,
        "runtime/case/testcase/input.txt",
        "runtime/case/.check",
        "runtime/case/cpu.slurm",
        "runtime/scripts/env.sh",
    ]
    (destination / "app.json").write_text(json.dumps(app_data, indent=2) + "\n", encoding="utf-8")
    package_base = name[6:] if name.startswith("scnet-") else name
    package_name = package_base + "-0.1.0-cpu.tar"
    delivery = json.loads((destination / "delivery.json").read_text(encoding="utf-8"))
    delivery.update({"package_name": package_name, "module_name": package_base + "/0.1.0-cpu",
                     "runtime_evidence": "runtime.json"})
    (destination / "delivery.json").write_text(json.dumps(delivery, indent=2) + "\n", encoding="utf-8")
    for markdown in destination.rglob("*.md"):
        text = markdown.read_text(encoding="utf-8")
        text = text.replace("This generated application is unverified.", "This generated application passed a local CPU smoke test.")
        text = text.replace("本应用尚未验证。", "本应用已通过本地 CPU smoke 测试。")
        markdown.write_text(text, encoding="utf-8")

    run = subprocess.run([find_bash(), "scripts/run.sh"], cwd=destination, text=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if run.returncode:
        raise ValueError("generated CPU smoke failed: " + run.stderr.strip())
    check = subprocess.run([sys.executable, "scripts/check.py", "results"], cwd=destination,
                           text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check.returncode:
        raise ValueError("generated CPU checker failed: " + check.stderr.strip())
    package = write_runtime_tar(destination, package_name)
    manifest = {
        "kind": "cpu-quick-build", "build_system": build_system,
        "source_sha256": digest, "binary": binary_name,
        "smoke": {"input": smoke_input, "expected": expected, "status": "passed"},
        "runtime_tar": package_name,
        "runtime_tar_sha256": hashlib.sha256(package.read_bytes()).hexdigest(),
        "compute_verified": False,
    }
    (destination / "quick-build.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    scnet_app.load_app(destination)
    return {"application": str(destination), "build_system": build_system, "binary": binary_name,
            "source_sha256": digest, "runtime_tar": str(package),
            "quick_build": str(destination / "quick-build.json"),
            "smoke": "passed", "compute_verified": False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--upstream", required=True)
    parser.add_argument("--input", default="hello\n")
    parser.add_argument("--expected", default="hello\n")
    parser.add_argument("--binary")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(build(args.source, args.output, args.name, args.upstream,
                               args.input, args.expected, args.binary), indent=2))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print("scnet-quickbuild: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
