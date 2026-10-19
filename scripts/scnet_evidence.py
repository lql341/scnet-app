"""Private local acceptance records; no hardware certification or submission engine."""
from __future__ import annotations

import datetime
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys

JOB_STATES = ("unknown", "succeeded", "failed", "cancelled", "job_timeout", "wait_timeout", "budget_stopped")


def read_object(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=invalid_constant)
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object: " + str(path))
    return value


def invalid_constant(value):
    raise ValueError("Non-finite JSON constant: " + value)


def safe_file(root, name):
    root = Path(root).resolve()
    pure = PurePosixPath(name)
    if not name or pure.is_absolute() or ".." in pure.parts or "\\" in name or ":" in name or any(ord(c) < 32 for c in name):
        raise ValueError("Expected a relative artifact path: " + name)
    path = root / name
    path.resolve().relative_to(root)
    if not path.is_file() or any((root / Path(*pure.parts[:i])).is_symlink() for i in range(1, len(pure.parts) + 1)):
        raise ValueError("Artifact is missing or uses a symlink: " + name)
    return path


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode("utf-8")).hexdigest()


def stack_signature(data, binding):
    stack = data.get("stack")
    if not stack:
        return None
    result = json.loads(json.dumps(stack))
    result["platform"] = {
        **result.get("platform", {}),
        "adapter": "scnet-" + binding["scnet"]["backend"],
        "region": binding["scnet"]["region"],
        "cluster": binding["scnet"]["cluster"],
        "queue": binding["scnet"]["queue"],
    }
    return result


def source_hashes(root, data):
    names = sorted(set(["app.json", data["run"], data["check"], *data["files"]]))
    if (Path(root) / "delivery.json").is_file():
        names.append("delivery.json")
    return {name: sha256(safe_file(root, name)) for name in names}


def seconds(value):
    hours, minutes, secs = map(int, value.split(":"))
    return hours * 3600 + minutes * 60 + secs


def finite(value):
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def validate_checks(checks):
    names = set()
    for item in checks:
        if item["name"] in names:
            raise ValueError("Duplicate check name: " + item["name"])
        names.add(item["name"])
        if item["kind"] == "numeric":
            if not all(key in item for key in ("file", "key", "ref")) or "criterion" in item:
                raise ValueError("Numeric checks require file, key and ref; no criterion")
            if not finite(item["ref"]) or any(not finite(item.get(key, 0)) or item.get(key, 0) < 0 for key in ("atol", "rtol")):
                raise ValueError("Reference and nonnegative tolerances must be finite")
            if not finite(item.get("atol", 0) + item.get("rtol", 0) * abs(item["ref"])):
                raise ValueError("Combined numeric tolerance must remain finite")
            pure = PurePosixPath(item["file"])
            if pure.is_absolute() or ".." in pure.parts or "\\" in item["file"] or ":" in item["file"] or any(ord(c) < 32 for c in item["file"]):
                raise ValueError("Numeric check file must be a relative result path")
        elif not item.get("criterion", "").strip() or any(key in item for key in ("file", "key", "ref", "atol", "rtol")):
            raise ValueError("Hook checks require a criterion; numeric fields are not allowed")
    if checks and not any(item["required"] for item in checks):
        raise ValueError("At least one check must be required")


def numeric_rows(checks, results):
    rows = {}
    for item in checks:
        if item["kind"] != "numeric":
            continue
        value, error = None, None
        try:
            value = read_object(safe_file(results, item["file"])).get(item["key"])
            if not finite(value):
                error = "Missing or non-finite numeric observation"
        except (OSError, ValueError) as exc:
            error = str(exc)
        tolerance = item.get("atol", 0) + item.get("rtol", 0) * abs(item["ref"])
        rows[item["name"]] = {"observed": value if finite(value) else None,
                              "passed": error is None and abs(value - item["ref"]) <= tolerance,
                              "error": error}
    return rows


def evaluate(checks, numeric, hook, hook_ok):
    verdicts = hook.get("checks", {}) if isinstance(hook.get("checks", {}), dict) else {}
    return [{"name": item["name"], "required": item["required"], "holdout": item.get("holdout", False),
             **(numeric[item["name"]] if item["kind"] == "numeric" else {"passed": hook_ok and verdicts.get(item["name"]) is True})}
            for item in checks]


def check_job(command, job_id, remote, data, binding):
    """Check platform facts independently of the user's declared state; no allocation."""
    result = {"status": "unconfirmed", "job_id": job_id, "remote_dir": remote}
    try:
        proc = subprocess.run(command, capture_output=True, encoding="utf-8", timeout=120)
        if proc.returncode:
            raise ValueError("scnet-hpc job failed: " + proc.stderr[:1000])
        job = json.loads(proc.stdout)
        if not isinstance(job, dict):
            raise ValueError("scnet-hpc job did not return an object")
        fields = ("job_id", "state", "source", "state_confirmed", "queue", "work_dir", "nodes", "cpus", "dcus", "exit_code", "platform_exit_status")
        result["job"] = {key: job[key] for key in fields if key in job}
        expected = {"job_id": str(job_id), "queue": binding["scnet"]["queue"], "work_dir": remote,
                    "nodes": str(data["resources"]["nodes"]), "cpus": str(data["resources"]["cpus"]),
                    "dcus": str(data["resources"]["dcus_per_node"])}
        missing = [key for key, value in expected.items() if str(job.get(key)) != value]
        exits = [str(job[key]) for key in ("exit_code", "platform_exit_status") if job.get(key) is not None]
        confirmed = job.get("source") == "history" or job.get("state_confirmed") is True
        if not missing and job.get("state") == "COMPLETED" and confirmed and exits and all(code in ("0", "0:0") for code in exits):
            result["status"] = "passed"
        result["mismatched_or_missing"] = missing
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        result["error"] = str(exc)
    return result


def record(root, data, binding, results, run_id, artifacts, job_state="unknown", job_command=None, job_id=None, remote=None, timeout=300):
    root, results = Path(root).resolve(), Path(results).resolve()
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}", run_id):
        raise ValueError("Run ID must be 1-64 letters/digits/dots/underscores/hyphens")
    if job_state not in JOB_STATES or not 1 <= timeout <= 3600:
        raise ValueError("Invalid job state or checker timeout (1-3600 seconds)")
    if not results.is_dir():
        raise ValueError("Results must be a collected local directory")
    folder = root / ".private" / "evidence" / run_id
    if any(path.is_symlink() for path in (root / ".private", root / ".private/evidence")):
        raise ValueError("Private evidence directory cannot be a symlink")
    check_files = [item["file"] for item in data["checks"] if item["kind"] == "numeric"]
    missing = sorted(set(name for name in check_files if not (results / name).exists()))
    names = sorted(set(artifacts + [name for name in check_files if name not in missing]))
    if not names:
        raise ValueError("Declare at least one result/log artifact")
    originals = {name: safe_file(results, name) for name in names}
    before_source = source_hashes(root, data)
    folder.mkdir(parents=True, exist_ok=False)
    snapshot = folder / "artifacts"
    for name, source in originals.items():
        target = snapshot / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    before = {name: sha256(safe_file(snapshot, name)) for name in names}
    numeric = numeric_rows(data["checks"], snapshot)
    hook, hook_exit, error = {}, None, None
    stdout, stderr = b"", b""
    if job_state not in ("failed", "cancelled", "job_timeout", "budget_stopped"):
        try:
            proc = subprocess.run([sys.executable, str(safe_file(root, data["check"])), str(snapshot)],
                                  cwd=folder, capture_output=True, timeout=timeout)
            hook_exit, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
            try:
                hook = json.loads(stdout.decode("utf-8"), parse_constant=invalid_constant) if stdout.strip() else {}
                if not isinstance(hook, dict):
                    hook = {}
            except (ValueError, UnicodeError):
                hook = {}
        except subprocess.TimeoutExpired as exc:
            error, stdout, stderr = "checker_timeout", exc.stdout or b"", exc.stderr or b""
        except OSError as exc:
            error = "checker_error: " + str(exc)
    else:
        error = "checker_skipped_for_unsuccessful_job"
    (folder / "checker.stdout.txt").write_bytes(stdout)
    (folder / "checker.stderr.txt").write_bytes(stderr)
    try:
        unchanged = before == {name: sha256(safe_file(snapshot, name)) for name in names} and before_source == source_hashes(root, data)
    except (OSError, ValueError):
        unchanged = False
    rows = evaluate(data["checks"], numeric, hook, hook_exit == 0)
    passed = unchanged and hook_exit == 0 and all(row["passed"] for row in rows if row["required"])
    job = check_job(job_command, job_id, remote, data, binding) if job_command else {"status": "not_checked"}
    signature = stack_signature(data, binding)
    validation = data.get("validation", {})
    entry = {"evidence_version": 2, "run_id": run_id,
             "recorder_version": (Path(__file__).resolve().parent.parent / "VERSION").read_text(encoding="utf-8").strip(),
             "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "source_hashes": before_source, "binding": binding, "result_hashes": before, "missing_check_files": missing,
             "stack_signature": signature,
             "stack_fingerprint": fingerprint(signature) if signature else None,
             "criterion_version": validation.get("criterion_version"),
             "declared_job_state": job_state, "source": "scnet_job_checked" if job["status"] == "passed" else "self_reported",
             "scheduler": job, "checker_exit": hook_exit, "checker_error": error,
             "inputs_unchanged": unchanged, "hook_result": hook, "checks": rows,
             "correctness": "passed" if passed else "failed",
             "runtime": "not_assessed", "compute_verified": False}
    entry["record_sha256"] = fingerprint(entry)
    with (folder / "record.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(entry, indent=2, allow_nan=False) + "\n")
    return {"evidence": str(folder / "record.json"), **summary(entry)}


def summary(entry=None):
    return {"compute_verified": False, "verification": {
        "correctness": entry["correctness"] if entry else "not_recorded",
        "scheduler": entry["scheduler"]["status"] if entry else "not_checked",
        "runtime": "not_assessed", "source": entry["source"] if entry else "none",
        "run_id": entry["run_id"] if entry else None}}


def verification(root, data, binding):
    root = Path(root).resolve()
    current = source_hashes(root, data)
    stale, invalid, entries = 0, 0, []
    for path in (root / ".private/evidence").glob("*/record.json"):
        try:
            path.resolve().relative_to(root)
            entry = read_object(path)
            digest = entry.pop("record_sha256")
            if entry.get("evidence_version") not in (1, 2) or fingerprint(entry) != digest:
                raise ValueError("Record checksum mismatch")
            if entry["source_hashes"] != current or entry["binding"] != binding:
                stale += 1
                continue
            results = path.parent / "artifacts"
            if not entry["inputs_unchanged"] or any(sha256(safe_file(results, name)) != digest for name, digest in entry["result_hashes"].items()):
                raise ValueError("Result artifact changed")
            rows = evaluate(data.get("checks", []), numeric_rows(data.get("checks", []), results), entry["hook_result"], entry["checker_exit"] == 0)
            if rows != entry["checks"]:
                raise ValueError("Check outcomes differ from recorded artifacts")
            entries.append(entry)
        except (OSError, ValueError, KeyError, TypeError):
            invalid += 1
    latest = max(entries, key=lambda entry: entry["recorded_at"]) if entries else None
    return {**summary(latest), "stale_evidence": stale, "invalid_evidence": invalid}
