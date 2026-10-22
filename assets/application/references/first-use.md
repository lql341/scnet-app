# First use

This application skill can be inspected offline, but a real SCNet job requires
an activated account, credentials, a region/queue and a deployed application
module.

## 1. Account and resources

- The SCNet account must be enabled for the target region and queue. AK/SK alone
  does not activate compute resources.
- If the account is not activated, follow the official SCNet activation path and
  stop before configuring credentials or submitting a job.
- SSH is needed only for deployment or diagnosis; normal OpenAPI runs do not use
  SSH.

## 2. Credentials

Use environment variables in the user's own terminal:

```text
SCNET_OPENAPI_USER
SCNET_OPENAPI_ACCESS_KEY
SCNET_OPENAPI_SECRET_KEY
```

If `scnet-hpc` is installed, use its setup wizard in your own terminal:

```bash
python3 "<scnet-hpc>/scripts/scnet.py" setup new --mode openapi
python3 "<scnet-hpc>/scripts/scnet.py" setup status
```

Never send AK/SK, private keys or credential files to the agent/chat.

## 3. Local check

```bash
python3 scripts/doctor.py
python3 scripts/doctor.py --json
python3 scripts/doctor.py --require-openapi
```

The generated bridge template uses the `scnet-hpc` CLI for upload, submit, wait
and collection. Its doctor therefore treats a missing `scnet-hpc` as a dependency
blocker. It reuses `scnet-hpc doctor --json --no-network` to inspect the shared
credential store; it does not create a second credential store. If the store
cannot be inspected, credentials are reported as `unknown`, not `missing`.
Only an application that actually embeds the pinned adapter may treat
`scnet-hpc` as optional.

`openapi_ready` covers local prerequisites only. It does not prove account
activation, module deployment or device availability. It never prints secret
values and never submits a job.

## 4. Application readiness

- Replace the stock `scripts/run.sh` and `scripts/check.py` markers.
- Record the module, target, runtime and device assumptions in `app.json` and
  `references/prerequisites_CN.md`.
- Run the application-specific probe and a bounded smoke case on a compute node
  before any production run.
- Keep private paths, hostnames, job IDs and scheduler logs outside the repository.
