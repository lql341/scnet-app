#!/usr/bin/env python3
"""Integrate scientific apps with SCNet resources, scheduling and packaging plans."""
from __future__ import annotations

import argparse
import datetime
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

import scnet_evidence as evidence
import scnet_delivery as delivery
import scnet_level_a as level_a

ROOT = Path(__file__).resolve().parent.parent
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
DEFAULT_ACCEPTANCE = "Define an application-specific reference result and numerical/functional acceptance criteria before running."
DEFAULT_STACK = {
    "system": {"name": "unconfigured", "glibc": "unconfigured"},
    "toolchain": {"gcc": "unconfigured", "cmake": "unconfigured"},
    "backend": {"kind": "dcu", "runtime": "unconfigured", "version": "unconfigured",
                "target": "unconfigured", "arch": "unconfigured"},
    "mpi": {"vendor": "unconfigured", "version": "unconfigured"},
    "framework": {"name": "none"},
    "platform": {"adapter": "scnet-openapi", "region": "0", "cluster": "unconfigured", "queue": "unconfigured"},
}


def default_stack(target):
    value = json.loads(json.dumps(DEFAULT_STACK))
    value["backend"]["kind"] = "dcu" if target == "hygon-z100" else "cpu"
    value["backend"]["target"] = target if target == "hygon-c86" else "unconfigured"
    return value


class AppError(ValueError):
    pass


def emit(value):
    # ASCII JSON survives native Windows stdout code pages and redirected files.
    print(json.dumps(value, ensure_ascii=True, indent=2), flush=True)


def check_schema(value, schema, where="app"):
    """Evaluate exactly the JSON Schema keywords used by our bundled schema."""
    kind = schema.get("type")
    types = {"object": dict, "array": list, "string": str, "integer": int, "number": (int, float), "boolean": bool}
    if kind and (not isinstance(value, types[kind]) or kind in ("integer", "number") and isinstance(value, bool)):
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
        if len(value) < schema.get("minItems", 0):
            raise AppError(where + " has too few items")
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


def stack_signature(data, binding=None):
    stack = data.get("stack")
    if not stack:
        return None
    result = json.loads(json.dumps(stack))
    if binding:
        result["platform"] = {
            **result.get("platform", {}),
            "adapter": "scnet-" + binding["scnet"]["backend"],
            "region": binding["scnet"]["region"],
            "cluster": binding["scnet"]["cluster"],
            "queue": binding["scnet"]["queue"],
        }
    return result


def stack_is_configured(stack):
    if not stack:
        return True
    values = []
    for axis in ("system", "toolchain", "backend", "mpi", "framework", "platform"):
        values.extend(stack[axis].values())
    return all(value not in ("", "0", "unconfigured") for value in values)


def target_short_name(target):
    return {"hygon-z100": "z100", "hygon-c86": "c86"}.get(target, target)


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
        raise AppError("Hygon Z100 DCU target requires an explicit DCU allocation; no CPU fallback")
    if data["target"] == "hygon-c86" and data["resources"]["dcus_per_node"] != 0:
        raise AppError("C86 CPU target must request zero DCUs")
    if not any(int(part) for part in data["resources"]["walltime"].split(":")):
        raise AppError("walltime must be positive")
    if data["environment"]["modulefiles"]:
        remote_path(data["environment"]["modulefiles"])
    if data.get("stack"):
        stack = data["stack"]
        if stack["backend"]["target"] not in ("unconfigured", data["target"]):
            raise AppError("stack.backend.target must match target")
        if data["target"] == "hygon-z100" and stack["backend"]["kind"] not in ("dcu", "unconfigured"):
            raise AppError("Hygon Z100 target requires a DCU backend")
        if data["target"] == "hygon-c86" and stack["backend"]["kind"] not in ("cpu", "unconfigured"):
            raise AppError("Hygon C86 target requires a CPU backend")
    evidence.validate_checks(data.get("checks", []))
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
        "scnet": {"backend": "openapi", "cluster": "unconfigured", "region": "0", "queue": "unconfigured"},
        "resources": {"nodes": 1, "cpus": 8, "dcus_per_node": 1 if target == "hygon-z100" else 0, "walltime": "00:03:00"},
        "environment": {"modules": [], "modulefiles": ""},
        "stack": default_stack(target),
        "prerequisites": {"modules": [], "conflicts": [], "obtain": "Complete references/prerequisites_CN.md before deployment."},
        "validation": {"criterion_version": "level-a-v1", "standard_suites": ["level-a"]},
        "run": "scripts/run.sh", "check": "scripts/check.py", "files": [],
        "acceptance": DEFAULT_ACCEPTANCE,
        "provenance": {"revision": "", "license": ""},
        "budget": {"max_nodes": 1, "max_cpus": 8, "max_dcus_per_node": 1 if target == "hygon-z100" else 0,
                   "max_walltime": "00:03:00"},
        "checks": [{"name": "primary", "kind": "hook", "required": True, "criterion": DEFAULT_ACCEPTANCE}]
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
            if any(part in ("__pycache__", ".git") for part in relative.parts) or source.suffix == ".pyc":
                continue
            path = destination / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            text = (source.read_text(encoding="utf-8").replace("__APP_NAME__", name)
                    .replace("__UPSTREAM__", upstream).replace("__TARGET__", target)
                    .replace("__PACKAGE_X__", name[6:][:20])
                    .replace("__PACKAGE_Z__", "hygon_dtk" if target == "hygon-z100" else "hygon_c86"))
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
    return data["acceptance"] != DEFAULT_ACCEPTANCE and all(item.get("criterion") != DEFAULT_ACCEPTANCE for item in data.get("checks", [])) and all(
        "SCNET_APP_UNIMPLEMENTED" not in local_file(Path(root), data[key]).read_text(encoding="utf-8")
        for key in ("run", "check")
    )


def resolve_binding(data, path=None):
    binding = {"scnet": data["scnet"], "budget": data.get("budget")}
    if path:
        override = evidence.read_object(Path(path))
        if set(override) != {"scnet", "budget"}:
            raise AppError("binding file requires exactly scnet and budget")
        schema = evidence.read_object(ROOT / "schema/app.schema.json")["properties"]
        for key in override:
            check_schema(override[key], schema[key], "binding." + key)
        binding = override
    return binding


def deployment_blocks(data, binding):
    reasons = []
    if binding["scnet"]["region"] == "0" or any(binding["scnet"][key] == "unconfigured" for key in ("cluster", "queue")):
        reasons.append("Select an enabled SCNet cluster/region/queue in app.json or --binding.")
    stack = stack_signature(data, binding)
    if stack and not stack_is_configured(stack):
        reasons.append("Declare a complete six-axis stack signature before deployment.")
    elif stack and stack["platform"]["adapter"] != "scnet-" + binding["scnet"]["backend"]:
        reasons.append("stack.platform.adapter must match the selected SCNet backend.")
    source = data.get("provenance", {})
    if not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", source.get("revision", "")) or not source.get("license", "").strip():
        reasons.append("Record the exact upstream commit/archive SHA256 and license in provenance.")
    budget = binding["budget"]
    if not budget:
        reasons.append("Declare an authorized per-job resource budget in app.json or --binding.")
    else:
        for field in ("nodes", "cpus", "dcus_per_node", "walltime"):
            requested, maximum = data["resources"][field], budget["max_" + field]
            if field == "walltime":
                requested, maximum = evidence.seconds(requested), evidence.seconds(maximum)
            if requested > maximum:
                reasons.append("Resource request exceeds budget: " + field)
    return reasons


def plan(root, hpc, remote, binding_path=None):
    data = load_app(root)
    root = Path(root).resolve()
    remote = remote_path(remote)
    binding = resolve_binding(data, binding_path)
    bound = {**data, "scnet": binding["scnet"]}
    base = base_argv(bound, hpc)
    script = ["set -euo pipefail", "cd " + shlex.quote(remote)]
    environment = data["environment"]
    if environment["modulefiles"]:
        script.append("module use " + shlex.quote(environment["modulefiles"]))
    script += ["module load " + shlex.quote(name) for name in environment["modules"]]
    script += ["mkdir -p results", "exec bash " + shlex.quote(data["run"])]
    command = shlex.join(["bash", "-l", "-c", "\n".join(script)])
    resources = data["resources"]
    submit = ["submit", "--name", data["name"], "--queue", binding["scnet"]["queue"],
              "--nodes", "1", "--cpus", str(resources["cpus"]),
              "--dcus", str(resources["dcus_per_node"]), "--walltime", resources["walltime"],
              "--work-dir", remote, "--command", command]
    files = sorted(set(["app.json", data["run"], data["check"], *data["files"]]))
    directories = sorted(set([remote, remote + "/results"] + [remote + "/" + str(PurePosixPath(f).parent) for f in files if str(PurePosixPath(f).parent) != "."]))
    ready = implementation_ready(root, data)
    blocked = deployment_blocks(data, binding)
    blocked.extend(delivery.attempt_blocks(root))
    if not ready:
        blocked.append("Implement run/check hooks and replace the stock acceptance condition.")
    status = evidence.verification(root, data, binding)
    return {
        "application": data["name"], "target": data["target"], **status,
        "stack_signature": stack_signature(data, binding),
        "binding": binding,
        "implementation_ready": ready,
        "blocked_by": blocked,
        "effects": "No commands executed. Review the plan; pass live preflight and implement hooks before any remote mutation.",
        "remote_directory_rule": "Use a fresh dedicated path for each run; this planner does not reserve it.",
        "preflight": [base + ["doctor"], base + ["resource-summary"]],
        "prepare": [base + ["mkdir", directory, "--parents"] for directory in directories],
        "upload": [base + ["upload", str(root / relative), str(PurePosixPath(remote + "/" + relative).parent)] for relative in files],
        "preview": hpc + ["--dry-run"] + base[len(hpc):] + submit,
        "submit": base + submit if not blocked else None,
        "follow_up": {
            "status": base + ["job", "<job-id>"],
            "wait": base + ["wait", "<job-id>", "--wait-timeout", "900", "--interval", "15"],
            "files": base + ["files", remote + "/results"],
            "download": "Use scnet-hpc download for each explicit result/log path; then run the local check hook.",
            "check": [sys.executable, str(root / data["check"]), "<local-results-directory>"],
            "cancel": base + ["cancel", "<job-id>"]
        }
    }


def record(root, results, run_id, artifacts, binding_path=None, job_state="unknown", hpc=None, job_id=None, remote=None, timeout=300):
    data = load_app(root)
    if not implementation_ready(root, data) or not data.get("checks"):
        raise AppError("Implement hooks, acceptance and structured checks before recording.")
    binding = resolve_binding(data, binding_path)
    job_command = None
    if job_id:
        if not hpc or not remote or deployment_blocks(data, binding):
            raise AppError("Job verification requires a configured binding, provenance, budget and --remote-dir.")
        remote = remote_path(remote)
        job_command = base_argv({**data, "scnet": binding["scnet"]}, hpc) + ["--details", "job", job_id]
    return evidence.record(root, data, binding, results, run_id, artifacts, job_state, job_command, job_id, remote, timeout)


WORKFLOW_STATES = (
    "intake", "inspect", "classify", "plan", "cpu_build", "cpu_validate",
    "dcu_probe", "dcu_port", "dcu_validate", "package", "clean_install", "release",
)
WORKFLOW_TERMINAL = ("passed", "blocked", "failed")
WORKFLOW_FAILURE_CLASSES = (
    "retry_same", "change_strategy", "needs_porting", "needs_user_decision", "unsupported",
)


def _workflow_dir(root):
    return Path(root).resolve() / ".private" / "workflow"


def _workflow_state_path(root):
    return _workflow_dir(root) / "state.json"


def _workflow_timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _workflow_read(root):
    path = _workflow_state_path(root)
    if not path.is_file() or path.is_symlink():
        raise AppError("workflow has not been initialized; run intake first")
    state = evidence.read_object(path)
    if state.get("workflow_version") != 1 or state.get("current_state") not in WORKFLOW_STATES:
        raise AppError("workflow state is invalid")
    return state


def _workflow_write(root, state):
    directory = _workflow_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / "state.json.tmp"
    temporary.write_text(json.dumps(state, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    temporary.replace(directory / "state.json")


def _workflow_max_attempts(root):
    path = Path(root).resolve() / "delivery.json"
    if not path.is_file():
        return 1
    try:
        value = evidence.read_object(path).get("max_attempts", 1)
    except (OSError, ValueError):
        return 1
    return value if type(value) is int and 1 <= value <= 100 else 1


def _workflow_next_state(state, data):
    current = state["current_state"]
    if current == "classify":
        return "cpu_build" if data["target"] == "hygon-c86" else "cpu_build"
    if current == "cpu_validate":
        return "package" if data["target"] == "hygon-c86" else "dcu_probe"
    if current == "dcu_validate":
        return "package"
    if current == "clean_install":
        return "release"
    index = WORKFLOW_STATES.index(current)
    return WORKFLOW_STATES[index + 1] if index + 1 < len(WORKFLOW_STATES) else current


def _workflow_failure_class(stage, reason):
    text = reason.lower()
    if stage in ("dcu_probe", "dcu_port", "dcu_validate") or "compute" in text or "dcu" in text:
        return "needs_porting"
    if any(word in text for word in ("region", "queue", "budget", "binding", "license", "provenance", "authorization")):
        return "needs_user_decision"
    if stage in ("cpu_build", "package", "clean_install"):
        return "change_strategy"
    return "unsupported"


def _workflow_attempt(root, state, result, failure=None):
    attempts = _workflow_dir(root) / "attempts"
    attempts.mkdir(parents=True, exist_ok=True)
    number = state["step_attempt"] + 1
    attempt = attempts / f"{number:04d}"
    if attempt.exists():
        raise AppError("workflow attempt directory already exists: " + str(attempt))
    attempt.mkdir()
    (attempt / "request.json").write_text(json.dumps({
        "workflow_version": 1, "state": state["current_state"], "attempt": number,
        "retries_used_before": state["retries_used"],
        "created_at": _workflow_timestamp(),
    }, indent=2) + "\n", encoding="utf-8")
    (attempt / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    if failure:
        (attempt / "failure.json").write_text(json.dumps(failure, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return number, attempt


def _workflow_execute(root, state, data):
    stage = state["current_state"]
    if stage == "inspect":
        load_app(root)
        return {"status": "passed", "detail": "application descriptor and declared files are readable"}
    if stage == "classify":
        strategy = "cpu-oracle-then-dcu" if data["target"] == "hygon-z100" else "cpu-build"
        return {"status": "passed", "strategy": strategy, "target": data["target"]}
    if stage == "plan":
        preview = plan(root, ["scnet-hpc"], "/workflow/offline-preview")
        if preview["blocked_by"]:
            return {"status": "blocked", "detail": "offline plan is blocked", "blocked_by": preview["blocked_by"]}
        return {"status": "passed", "detail": "offline plan generated", "submit_available": bool(preview["submit"])}
    if stage == "cpu_build":
        runtime_app = Path(root) / "runtime" / "app"
        if not runtime_app.is_dir() or not any(runtime_app.rglob("*")):
            return {"status": "blocked", "detail": "runtime/app is not populated; a CPU build or staged executable is required"}
        return {"status": "passed", "detail": "runtime/app is populated"}
    if stage == "cpu_validate":
        status = evidence.verification(root, data, resolve_binding(data))
        if status["verification"]["correctness"] != "passed":
            return {"status": "blocked", "detail": "a passing CPU correctness record is required", "verification": status}
        return {"status": "passed", "detail": "current CPU correctness evidence passed", "verification": status}
    if stage in ("dcu_probe", "dcu_port", "dcu_validate"):
        return {"status": "blocked", "detail": "compute-node DCU evidence is required; offline workflow does not claim accelerator support"}
    if stage == "package":
        status = delivery.gate(root, data, resolve_binding(data), evidence.verification(root, data, resolve_binding(data)),
                               implementation_ready(root, data), deployment_blocks(data, resolve_binding(data)))
        if not status["ready_to_build"]:
            return {"status": "blocked", "detail": "delivery gate is not ready", "blocked_by": status["blocked_by"]}
        return {"status": "passed", "detail": "delivery gate passed"}
    if stage == "clean_install":
        return {"status": "blocked", "detail": "clean-install replay requires a built package in a fresh output directory"}
    if stage == "release":
        return {"status": "blocked", "detail": "release requires an explicit build and reviewed compatibility report"}
    return {"status": "failed", "detail": "unknown workflow state"}


def workflow_intake(root):
    root = Path(root).resolve()
    if _workflow_state_path(root).exists():
        raise AppError("workflow already initialized; use status or resume")
    data = load_app(root)
    state = {
        "workflow_version": 1, "application": data["name"], "application_root": str(root),
        "current_state": "intake", "status": "active", "step_attempt": 0,
        "retries_used": 0,
        "max_attempts": _workflow_max_attempts(root), "history": [], "last_failure": None,
        "created_at": _workflow_timestamp(), "updated_at": _workflow_timestamp(),
    }
    number, attempt = _workflow_attempt(root, state, {"status": "passed", "detail": "intake accepted", "application": data["name"]})
    state["step_attempt"] = number
    state["history"].append({"attempt": number, "state": "intake", "status": "passed", "path": str(attempt.relative_to(root))})
    state["current_state"] = "inspect"
    state["updated_at"] = _workflow_timestamp()
    _workflow_write(root, state)
    return state


def workflow_run(root):
    root = Path(root).resolve()
    state = _workflow_read(root)
    if state["status"] != "active":
        raise AppError("workflow is not active; use resume before another run")
    if state["retries_used"] >= state["max_attempts"]:
        raise AppError("workflow retry limit reached; obtain a revised authorized limit")
    data = load_app(root)
    stage = state["current_state"]
    try:
        result = _workflow_execute(root, state, data)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {"status": "failed", "detail": str(exc)}
    failure = None
    if result["status"] in ("blocked", "failed"):
        failure = {
            "classification": _workflow_failure_class(
                stage, result.get("detail", "") + " " + " ".join(result.get("blocked_by", []))
            ),
            "state": stage, "reason": result.get("detail", ""), "created_at": _workflow_timestamp(),
        }
    number, attempt = _workflow_attempt(root, state, result, failure)
    state["step_attempt"] = number
    if result["status"] in ("blocked", "failed"):
        state["retries_used"] += 1
    state["history"].append({"attempt": number, "state": stage, "status": result["status"],
                             "path": str(attempt.relative_to(root))})
    if result["status"] == "passed":
        if stage == "release":
            state["status"] = "passed"
        else:
            state["current_state"] = _workflow_next_state(state, data)
    else:
        state["status"] = result["status"]
        state["last_failure"] = failure
    state["updated_at"] = _workflow_timestamp()
    _workflow_write(root, state)
    return {"state": state, "result": result, "attempt": number}


def workflow_resume(root):
    root = Path(root).resolve()
    state = _workflow_read(root)
    if state["status"] not in ("blocked", "failed"):
        raise AppError("workflow can only resume from blocked or failed")
    if state["retries_used"] >= state["max_attempts"]:
        raise AppError("workflow retry limit reached; obtain a revised authorized limit")
    state["status"] = "active"
    state["updated_at"] = _workflow_timestamp()
    state["history"].append({"event": "resume", "state": state["current_state"], "at": state["updated_at"]})
    _workflow_write(root, state)
    return state


def workflow_status(root):
    return _workflow_read(Path(root).resolve())


def workflow_explain_failure(root):
    state = _workflow_read(Path(root).resolve())
    failure = state.get("last_failure")
    if not failure:
        return {"status": state["status"], "message": "no recorded workflow failure", "current_state": state["current_state"]}
    messages = {
        "retry_same": "Retry the same stage after the transient condition is resolved.",
        "change_strategy": "Change the build or packaging strategy, then resume with a fresh attempt.",
        "needs_porting": "Complete target-runtime or DCU porting work before resuming.",
        "needs_user_decision": "Resolve the missing binding, authorization, provenance or license decision.",
        "unsupported": "The current workflow contract cannot support this stage or input.",
    }
    return {**failure, "guidance": messages.get(failure["classification"], "Review the recorded failure.")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="op", required=True)
    init = sub.add_parser("init", help="create a new application scaffold without overwriting")
    init.add_argument("name")
    init.add_argument("--output", type=Path, required=True)
    init.add_argument("--upstream", required=True)
    init.add_argument("--target", choices=["hygon-z100", "hygon-c86"], default="hygon-z100")
    for command in ("validate", "plan", "doctor", "record", "gate", "build", "level-a", "quick-build", "inspect-source",
                    "intake", "run", "status", "resume", "explain-failure"):
        child = sub.add_parser(command)
        if command in ("level-a", "quick-build"):
            if command == "level-a":
                child.add_argument("application", type=Path)
                child.add_argument("--output", type=Path, help="write structured level-A evidence JSON")
                continue
            child.add_argument("source", type=Path)
            child.add_argument("--output", type=Path, required=True)
            child.add_argument("--name", required=True)
            child.add_argument("--upstream", required=True)
            child.add_argument("--input", default="hello\n")
            child.add_argument("--expected", default="hello\n")
            child.add_argument("--binary")
            continue
        if command == "inspect-source":
            child.add_argument("source", type=Path)
            child.add_argument("--output", type=Path)
            continue
        child.add_argument("application", type=Path)
        child.add_argument("--binding", type=Path, help="external JSON with explicit scnet and budget objects")
        if command != "validate":
            child.add_argument("--scnet-hpc", type=Path)
        if command == "plan":
            child.add_argument("--remote-dir", required=True)
        if command == "record":
            child.add_argument("--results", type=Path, required=True)
            child.add_argument("--run-id", required=True)
            child.add_argument("--artifacts", nargs="+", required=True, help="explicit relative result/log files; numeric check files are also included")
            child.add_argument("--job-state", choices=evidence.JOB_STATES, default="unknown")
            child.add_argument("--job-id")
            child.add_argument("--remote-dir")
            child.add_argument("--checker-timeout", type=int, default=300)
        if command == "build":
            child.add_argument("--output", type=Path, required=True, help="fresh directory for skill and runtime tar")
    args = parser.parse_args(argv)
    try:
        if args.op == "init":
            emit(init_app(args.name, args.output, args.upstream, args.target))
        elif args.op == "level-a":
            result = level_a.run(args.application, args.output)
            emit(result)
            return 0 if result["passed"] else 1
        elif args.op == "quick-build":
            from scnet_quickbuild import build
            emit(build(args.source, args.output, args.name, args.upstream,
                       args.input, args.expected, args.binary))
            return 0
        elif args.op == "inspect-source":
            from scnet_intake import inspect
            emit(inspect(args.source, args.output))
            return 0
        elif args.op == "intake":
            emit(workflow_intake(args.application))
        elif args.op == "run":
            emit(workflow_run(args.application))
        elif args.op == "status":
            emit(workflow_status(args.application))
        elif args.op == "resume":
            emit(workflow_resume(args.application))
        elif args.op == "explain-failure":
            emit(workflow_explain_failure(args.application))
        elif args.op == "validate":
            data = load_app(args.application)
            emit({"application": data["name"], "packaging_ok": True,
                  "implementation_ready": implementation_ready(args.application, data),
                  "deployment_blocks": deployment_blocks(data, resolve_binding(data, args.binding)),
                  **evidence.verification(args.application, data, resolve_binding(data, args.binding))})
        elif args.op == "plan":
            emit(plan(args.application, hpc_cli(args.scnet_hpc), args.remote_dir, args.binding))
        elif args.op == "record":
            status = record(args.application, args.results, args.run_id, args.artifacts, args.binding, args.job_state,
                            hpc_cli(args.scnet_hpc) if args.job_id else None, args.job_id, args.remote_dir, args.checker_timeout)
            emit(status)
            return 0 if status["verification"]["correctness"] == "passed" and (not args.job_id or status["verification"]["scheduler"] == "passed") else 1
        elif args.op in ("gate", "build"):
            data = load_app(args.application)
            binding = resolve_binding(data, args.binding)
            status = delivery.gate(args.application, data, binding,
                                   evidence.verification(args.application, data, binding),
                                   implementation_ready(args.application, data), deployment_blocks(data, binding))
            if args.op == "gate":
                emit(status)
                return 0 if status["ready_to_build"] else 1
            emit(delivery.build(args.application, data, status, args.output))
        elif args.op == "doctor":
            data = load_app(args.application)
            binding = resolve_binding(data, args.binding)
            if binding["scnet"]["region"] == "0" or binding["scnet"]["cluster"] == "unconfigured" or binding["scnet"]["queue"] == "unconfigured":
                raise AppError("Select an actual SCNet cluster/region/queue before doctor.")
            data = {**data, "scnet": binding["scnet"]}
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
