#!/usr/bin/env python3
"""Offline first-use check for this generated application skill.

This is a bridge-template doctor: it reads non-secret values from app.json and
checks environment credentials only.  It does not read the shared credential
store, authenticate or submit a job.  If this application embeds an OpenAPI
adapter, replace the credential probe with the pinned adapter helper and keep
the same JSON envelope.
"""
import argparse
import json
import os
from pathlib import Path
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

    present = [key for key in ENV_KEYS if os.environ.get(key)]
    credentials = {
        "present": len(present) == len(ENV_KEYS),
        "source": "environment" if len(present) == len(ENV_KEYS) else "missing",
        "env_keys_present": present,
        "shared_store": "unknown",
    }
    scnet = app.get("scnet") or {}
    region = str(scnet.get("region") or "").strip()
    queue = str(scnet.get("queue") or "").strip()
    config_ready = bool(
        region
        and region != "0"
        and queue
        and queue.lower() != "unconfigured"
    )
    hpc = find_scnet_hpc()
    next_steps = []
    blocker = None
    if not credentials["present"]:
        blocker = "credentials"
        next_steps = [
            "configure OPENAPI credentials in your own terminal: "
            "SCNET_OPENAPI_USER/ACCESS_KEY/SECRET_KEY, or use scnet-hpc setup"
        ]
    elif not config_ready:
        blocker = "configuration"
        next_steps = [
            "set a real region and queue in app.json after confirming account activation"
        ]
    elif not hpc:
        next_steps = [
            "scnet-hpc is optional for setup/SSH; install it only when deployment or diagnosis is needed"
        ]
    else:
        next_steps = [
            "local prerequisites are ready; run the application-specific online check before submission"
        ]

    return {
        "schema_version": SCHEMA_VERSION,
        "ok": bool(credentials["present"] and config_ready),
        "application": app.get("name"),
        "target": app.get("target"),
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
            "credentials": "ready" if credentials["present"] else "missing",
            "configuration": "ready" if config_ready else "incomplete",
            "remote": "unknown",
        },
        "openapi_ready": bool(credentials["present"] and config_ready),
        "primary_blocker": blocker,
        "next_steps": next_steps,
        "first_use": "references/first-use.md",
    }


def render(status):
    lines = [
        "schema_version={}".format(status.get("schema_version")),
        "application={}".format(status.get("application") or "(unknown)"),
        "credentials={}".format(
            status.get("readiness", {}).get("credentials", "missing")
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
