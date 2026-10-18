#!/usr/bin/env python3
"""Scaffold scientific applications and plan SCNet jobs; no submission engine."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
DEFAULT_ACCEPTANCE = "Define an application-specific reference result and numerical/functional acceptance criteria before running."


class AppError(ValueError):
    pass


def emit(value):
    # ASCII JSON survives native Windows stdout code pages and redirected files.
    print(json.dumps(value, ensure_ascii=True, indent=2), flush=True)


def check_schema(value, schema, where="app"):
    """Evaluate exactly the JSON Schema keywords used by our bundled schema."""
    kind = schema.get("type")
    types = {"object": dict, "array": list, "string": str, "integer": int}
    if kind and (not isinstance(value, types[kind]) or kind == "integer" and isinstance(value, bool)):
        raise AppError(where + " must be " + kind)
    if "const" in schema and (value != schema["const"] or type(value) is not type(schema["const"])):
        raise AppError(where + " must equal " + repr(schema["const"]))
    if "enum" in schema and value not in schema["enum"]:
        raise AppError(where + " has an unsupported value")
    if isinstance(value, dict):
        missing = set(schema.get("required", [])) - set(value)
        extra = set(value) - set(schema.get("properties", {}))
        if missing:
            raise AppError(where + " missing fields: " + ", ".join(sorted(missing)))
        if extra and schema.get("additionalProperties") is False:
            raise AppError(where + " unknown fields: " + ", ".join(sorted(extra)))
        for key, child in schema.get("properties", {}).items():
            if key in value:
                check_schema(value[key], child, where + "." + key)
    if isinstance(value, list):
        for index, item in enumerate(value):
            check_schema(item, schema.get("items", {}), where + "[" + str(index) + "]")
    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            raise AppError(where + " has an invalid format")
        if len(value) < schema.get("minLength", 0):
            raise AppError(where + " is empty")
    if isinstance(value, int) and value < schema.get("minimum", value):
        raise AppError(where + " is below the minimum")


def remote_path(value):
    if not value.startswith("/") or ".." in PurePosixPath(value).parts or any(ord(c) < 32 for c in value):
        raise AppError("remote path must be absolute, without traversal/control characters")
    if value == "/":
        raise AppError("use a dedicated remote run directory")
    return value.rstrip("/")


def local_file(root, relative):
    pure = PurePosixPath(relative)
    if not relative or pure.is_absolute() or ".." in pure.parts or "\\" in relative or any(ord(c) < 32 for c in relative):
        raise AppError("artifact paths must be relative POSIX file paths")
    path = root / relative
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        raise AppError("artifact escapes application directory") from None
    if not path.is_file() or path.is_symlink():
        raise AppError("artifact is missing or a symlink: " + relative)
    return resolved


def load_app(root):
    root = Path(root).resolve()
    data = json.loads((root / "app.json").read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schema/app.schema.json").read_text(encoding="utf-8"))
    check_schema(data, schema)
    upstream = urlsplit(data["upstream"])
    if not upstream.hostname or upstream.username or upstream.password or upstream.query or upstream.fragment:
        raise AppError("upstream must be a public HTTPS project URL without credentials/query/fragment")
    if len(data["name"]) > 64:
        raise AppError("skill names must be at most 64 characters")
    if data["target"] == "hygon-z100" and data["resources"]["dcus_per_node"] < 1:
        raise AppError("Z100 target requires an explicit DCU allocation; no CPU fallback")
    if data["target"] == "hygon-c86" and data["resources"]["dcus_per_node"] != 0:
        raise AppError("C86 CPU target must request zero DCUs")
    if not any(int(part) for part in data["resources"]["walltime"].split(":")):
        raise AppError("walltime must be positive")
    if data["environment"]["modulefiles"]:
        remote_path(data["environment"]["modulefiles"])
    for relative in [data["run"], data["check"], *data["files"]]:
        local_file(root, relative)
    if not data["run"].endswith(".sh") or not data["check"].endswith(".py"):
        raise AppError("v1 uses a Bash run hook and a local Python result checker")
    return data


def init_app(name, output, upstream, target):
    destination = Path(output).resolve()
    if destination.exists():
        raise AppError("destination already exists; no files were overwritten")
    template = ROOT / "assets/application"
    try:
        destination.relative_to(template.resolve())
    except ValueError:
        pass
    else:
        raise AppError("destination must not be inside the source template")
    # Validate all metadata before creating the destination.
    schema = json.loads((ROOT / "schema/app.schema.json").read_text(encoding="utf-8"))
    data = {
        "schema_version": 1, "name": name, "upstream": upstream, "target": target,
        "scnet": {"backend": "openapi", "cluster": "kseshell", "region": "11250",
                  "queue": "kshdnormal" if target == "hygon-z100" else "kshcnormal"},
        "resources": {"nodes": 1, "cpus": 8, "dcus_per_node": 1 if target == "hygon-z100" else 0, "walltime": "00:03:00"},
        "environment": {"modules": [], "modulefiles": ""},
        "run": "scripts/run.sh", "check": "scripts/check.py", "files": [],
        "acceptance": DEFAULT_ACCEPTANCE
    }
    check_schema(data, schema)
    url = urlsplit(upstream)
    if len(name) > 64 or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise AppError("invalid application name or public upstream URL")
    # One mkdir claims the destination; a concurrent initializer cannot overwrite it.
    destination.mkdir(parents=True, exist_ok=False)
    for source in template.rglob("*"):
        if source.is_file():
            relative = source.relative_to(template)
            path = destination / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            text = source.read_text(encoding="utf-8").replace("__APP_NAME__", name).replace("__UPSTREAM__", upstream).replace("__TARGET__", target)
            with path.open("w", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
    (destination / "app.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(ROOT / "LICENSE", destination / "LICENSE")
    load_app(destination)
    return {"application": str(destination), "packaging_ok": True, "compute_verified": False,
            "next": "Implement run/check hooks, define acceptance criteria, then plan a bounded SCNet smoke test."}


def hpc_cli(path):
    root = path or os.getenv("SCNET_HPC_ROOT")
    if root is None:
        root = Path(os.getenv("CODEX_HOME") or Path.home() / ".codex") / "skills/scnet-hpc"
    root = Path(root).expanduser().resolve()
    script = root / "scripts/scnet.py"
    if not script.is_file():
        raise AppError("install scnet-hpc or provide --scnet-hpc /absolute/skill/root")
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match or tuple(map(int, match.groups())) < (0, 6, 13):
        raise AppError("scnet-hpc >= 0.6.13 is required; this adapter is tested with 0.6.13")
    return [sys.executable, str(script)]


def base_argv(data, hpc):
    return hpc + ["--backend", "openapi", "--cluster", data["scnet"]["cluster"], "--region", data["scnet"]["region"]]


def implementation_ready(root, data):
    return data["acceptance"] != DEFAULT_ACCEPTANCE and all(
        "SCNET_APP_UNIMPLEMENTED" not in local_file(Path(root), data[key]).read_text(encoding="utf-8")
        for key in ("run", "check")
    )


def plan(root, hpc, remote):
    data = load_app(root)
    root = Path(root).resolve()
    remote = remote_path(remote)
    base = base_argv(data, hpc)
    script = ["set -euo pipefail", "cd " + shlex.quote(remote)]
    environment = data["environment"]
    if environment["modulefiles"]:
        script.append("module use " + shlex.quote(environment["modulefiles"]))
    script += ["module load " + shlex.quote(name) for name in environment["modules"]]
    script += ["mkdir -p results", "exec bash " + shlex.quote(data["run"])]
    command = shlex.join(["bash", "-l", "-c", "\n".join(script)])
    resources = data["resources"]
    submit = ["submit", "--name", data["name"], "--queue", data["scnet"]["queue"],
              "--nodes", "1", "--cpus", str(resources["cpus"]),
              "--dcus", str(resources["dcus_per_node"]), "--walltime", resources["walltime"],
              "--work-dir", remote, "--command", command]
    files = sorted(set(["app.json", data["run"], data["check"], *data["files"]]))
    directories = sorted(set([remote, remote + "/results"] + [remote + "/" + str(PurePosixPath(f).parent) for f in files if str(PurePosixPath(f).parent) != "."]))
    ready = implementation_ready(root, data)
    return {
        "application": data["name"], "target": data["target"], "compute_verified": False,
        "implementation_ready": ready,
        "blocked_by": [] if ready else ["Implement run/check hooks and replace the stock acceptance condition."],
        "effects": "No commands executed. Review the plan; pass live preflight and implement hooks before any remote mutation.",
        "remote_directory_rule": "Use a fresh dedicated path for each run; this planner does not reserve it.",
        "preflight": [base + ["doctor"], base + ["resource-summary"]],
        "prepare": [base + ["mkdir", directory, "--parents"] for directory in directories],
        "upload": [base + ["upload", str(root / relative), str(PurePosixPath(remote + "/" + relative).parent)] for relative in files],
        "preview": hpc + ["--dry-run"] + base[len(hpc):] + submit,
        "submit": base + submit if ready else None,
        "follow_up": {
            "status": base + ["job", "<job-id>"],
            "wait": base + ["wait", "<job-id>", "--wait-timeout", "900", "--interval", "15"],
            "files": base + ["files", remote + "/results"],
            "download": "Use scnet-hpc download for each explicit result/log path; then run the local check hook.",
            "check": [sys.executable, str(root / data["check"]), "<local-results-directory>"],
            "cancel": base + ["cancel", "<job-id>"]
        }
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="op", required=True)
    init = sub.add_parser("init", help="create a new application scaffold without overwriting")
    init.add_argument("name")
    init.add_argument("--output", type=Path, required=True)
    init.add_argument("--upstream", required=True)
    init.add_argument("--target", choices=["hygon-z100", "hygon-c86"], default="hygon-z100")
    for command in ("validate", "plan", "doctor"):
        child = sub.add_parser(command)
        child.add_argument("application", type=Path)
        if command != "validate":
            child.add_argument("--scnet-hpc", type=Path)
        if command == "plan":
            child.add_argument("--remote-dir", required=True)
    args = parser.parse_args(argv)
    try:
        if args.op == "init":
            emit(init_app(args.name, args.output, args.upstream, args.target))
        elif args.op == "validate":
            data = load_app(args.application)
            emit({"application": data["name"], "packaging_ok": True,
                  "implementation_ready": implementation_ready(args.application, data), "compute_verified": False})
        elif args.op == "plan":
            emit(plan(args.application, hpc_cli(args.scnet_hpc), args.remote_dir))
        elif args.op == "doctor":
            data = load_app(args.application)
            base = base_argv(data, hpc_cli(args.scnet_hpc))
            results = []
            for operation in ("doctor", "resource-summary"):
                env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
                proc = subprocess.run(base + [operation], capture_output=True, encoding="utf-8", env=env, timeout=120)
                if proc.returncode:
                    raise AppError("scnet-hpc " + operation + " failed: " + proc.stderr.strip())
                results.append({"operation": operation, "result": json.loads(proc.stdout)})
            emit({"preflight": results, "compute_verified": False})
        return 0
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print("scnet-app: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
