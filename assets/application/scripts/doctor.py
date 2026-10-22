#!/usr/bin/env python3
"""Offline first-use check for this generated bridge-template skill.

The generated default uses the scnet-hpc CLI for credentials, uploads, submit,
wait and collection.  This check therefore treats a missing scnet-hpc as a
dependency blocker.  It reuses scnet-hpc's read-only `doctor --no-network` to
inspect the shared credential store; it does not implement a second credential
store and does not authenticate or submit a job.

If this application is changed to embed the pinned adapter, replace the
credential probe with the adapter helper and mark scnet-hpc optional in the
application-specific contract.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_VERSION = 1
ENV_KEYS = (
    "SCNET_OPENAPI_USER",
    "SCNET_OPENAPI_ACCESS_KEY",
    "SCNET_OPENAPI_SECRET_KEY",
)


def load_app():
    return json.loads((ROOT / "app.json").read_text(encoding="utf-8"))


def find_scnet_hpc():
    candidates = []
    if os.environ.get("SCNET_HPC_ROOT"):
        candidates.append(Path(os.environ["SCNET_HPC_ROOT"]).expanduser())
    candidates.extend(
        [
            ROOT.parent / "scnet-hpc",
            Path.home() / ".codex" / "skills" / "scnet-hpc",
            Path.home() / ".claude" / "skills" / "scnet-hpc",
        ]
    )
    for candidate in candidates:
        cli = candidate / "scripts" / "scnet.py"
        if cli.is_file():
            return cli
    return None


def _hpc_credentials(cli):
    """Return (present, source, error) using scnet-hpc's read-only check."""
    try:
        completed = subprocess.run(
            [sys.executable, str(cli), "--json", "doctor", "--no-network"],
            text=True,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, "unknown", str(exc)
    try:
        payload = json.loads(completed.stdout)
    except ValueError:
        return None, "unknown", "scnet-hpc doctor did not return JSON"
    data = payload.get("data")
    checks = data.get("checks") if isinstance(data, dict) else None
    if not isinstance(checks, list):
        return None, "unknown", "scnet-hpc doctor checks are malformed"
    credential = next(
        (
            item
            for item in checks
            if isinstance(item, dict) and item.get("name") == "openapi_credentials"
        ),
        None,
    )
    if credential is None or not isinstance(credential.get("ok"), bool):
        return None, "unknown", "scnet-hpc doctor has no credential result"
    if credential["ok"]:
        return True, "shared_store", None
    return False, "missing", None


def _credentials(hpc):
    present = [key for key in ENV_KEYS if os.environ.get(key)]
    credentials = {
        "present": None,
        "source": "unknown",
        "env_keys_present": present,
        "shared_store": "unknown",
        "detail": None,
    }
    if len(present) == len(ENV_KEYS):
        credentials.update(
            {"present": True, "source": "environment", "shared_store": "not_checked"}
        )
        return credentials
    if not hpc:
        credentials["detail"] = "scnet-hpc is required to inspect the shared credential store"
        return credentials
    present, source, error = _hpc_credentials(hpc)
    credentials["present"] = present
    credentials["source"] = source
    credentials["shared_store"] = "checked" if present is not None else "unknown"
    credentials["detail"] = error
    return credentials


def probe():
    try:
        app = load_app()
    except (OSError, ValueError) as exc:
        return {
            "schema_version": SCHEMA_VERSION,
            "ok": False,
            "error": "cannot read app.json: {}".format(exc),
            "next_steps": ["repair app.json before first use"],
        }

    hpc = find_scnet_hpc()
    credentials = _credentials(hpc)
    scnet = app.get("scnet") or {}
    region = str(scnet.get("region") or "").strip()
    queue = str(scnet.get("queue") or "").strip()
    config_ready = bool(
        region
        and region != "0"
        and queue
        and queue.lower() != "unconfigured"
    )
    dependency_ready = bool(hpc)
    ready = bool(dependency_ready and credentials["present"] is True and config_ready)

    if not dependency_ready:
        blocker = "scnet_hpc"
        next_steps = [
            "install scnet-hpc and set SCNET_HPC_ROOT; the bridge template uses its CLI"
        ]
    elif credentials["present"] is False:
        blocker = "credentials"
        next_steps = [
            "configure OPENAPI credentials in your own terminal, or use scnet-hpc setup"
        ]
    elif credentials["present"] is None:
        blocker = "credentials"
        next_steps = [
            "run scnet-hpc doctor --json --no-network to inspect the shared credential store"
        ]
    elif not config_ready:
        blocker = "configuration"
        next_steps = [
            "set a real region and queue in app.json after confirming account activation"
        ]
    else:
        blocker = None
        next_steps = [
            "local prerequisites are ready; run the application-specific online check before submission"
        ]

    return {
        "schema_version": SCHEMA_VERSION,
        "ok": ready,
        "application": app.get("name"),
        "target": app.get("target"),
        "dependencies": {
            "scnet_hpc": "ready" if dependency_ready else "missing",
        },
        "credentials": credentials,
        "configuration": {
            "region": region or None,
            "queue": queue or None,
            "modules": list((app.get("environment") or {}).get("modules") or []),
            "ready": config_ready,
        },
        "scnet_hpc": {
            "found": bool(hpc),
            "path": str(hpc) if hpc else None,
        },
        "readiness": {
            "credentials": (
                "ready"
                if credentials["present"] is True
                else "missing"
                if credentials["present"] is False
                else "unknown"
            ),
            "configuration": "ready" if config_ready else "incomplete",
            "remote": "unknown",
        },
        "openapi_ready": ready,
        "primary_blocker": blocker,
        "next_steps": next_steps,
        "first_use": "references/first-use.md",
    }


def render(status):
    lines = [
        "schema_version={}".format(status.get("schema_version")),
        "application={}".format(status.get("application") or "(unknown)"),
        "scnet_hpc={}".format(
            status.get("dependencies", {}).get("scnet_hpc", "unknown")
        ),
        "credentials={}".format(
            status.get("readiness", {}).get("credentials", "unknown")
        ),
        "configuration={}".format(
            status.get("readiness", {}).get("configuration", "incomplete")
        ),
        "readiness_remote={}".format(
            status.get("readiness", {}).get("remote", "unknown")
        ),
        "openapi_local_prerequisites={}".format(
            "ready" if status.get("openapi_ready") else "not_ready"
        ),
    ]
    if status.get("error"):
        lines.append("error={}".format(status["error"]))
    if status.get("primary_blocker"):
        lines.append("primary_blocker={}".format(status["primary_blocker"]))
    if status.get("next_steps"):
        lines.append("next:")
        lines.extend("  " + step for step in status["next_steps"])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable status")
    parser.add_argument(
        "--require-openapi",
        action="store_true",
        help="exit nonzero unless local OpenAPI prerequisites are ready",
    )
    args = parser.parse_args(argv)
    status = probe()
    if args.json:
        print(json.dumps(status, indent=2, ensure_ascii=False))
    else:
        print(render(status))
    return 2 if args.require_openapi and not status.get("openapi_ready") else 0


if __name__ == "__main__":
    sys.exit(main())
