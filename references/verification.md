# Acceptance and private evidence

English | [中文](verification_CN.md)

Use this after implementing the application and collecting its explicit outputs.
The authoring CLI remains Python 3.8+ standard library. It does not deploy software,
submit a job or certify hardware. The application's checker may need documented
local dependencies. Treat it as trusted application code: it executes locally and
is not a sandbox for arbitrary upstream scripts.

## Structured acceptance

Keep the human-readable `acceptance` explanation. Add `checks` to app.json:

```json
[
  {"name":"energy","kind":"numeric","required":true,
   "file":"metrics.json","key":"energy","ref":1.0,"atol":0.000001,"rtol":0.0001},
  {"name":"structure","kind":"hook","required":true,
   "criterion":"Validate the raw output schema and conservation constraints."}
]
```

Numeric files are relative to the collected results directory. `key` is a top-level
JSON object key; the value must be a finite number, not a boolean. Pass when
`abs(observed-ref) <= atol + rtol*abs(ref)`. Omitted tolerances default to zero;
zero tolerances support exact counts. Tolerances and the combined bound must be
finite and nonnegative. Use a domain checker for arrays, convergence, statistics,
units and other scientific semantics, rather than forcing every check into a scalar.

The checker takes the result snapshot directory as its first argument. It must
exit zero on success. For hook checks it must also emit a JSON object on stdout,
for example `{"checks":{"structure":true}}`; missing/false verdicts fail. Diagnostic
output belongs on stderr. A zero exit alone cannot pass a hook check. Numeric
checks are evaluated by scnet-app independently of checker verdicts.

At least one check must be `required: true`; all required checks and the checker
must pass. `holdout: true` is optional metadata for an independent case that was
not used to tune the adaptation. Explain its input/reference provenance; the flag
does not prove independence. Regression/reference cases may be more appropriate
than a model-style holdout for some applications.

Freeze acceptance and checker versions before collecting evidence. Record an exact
upstream commit or source-archive SHA256 and license in `provenance`. Include all
checker helpers, inputs and dependency lock/manifests in the explicit `files` list
so source hashes cover them. Existing app.json v1 remains readable: add optional
fields without deleting its acceptance text. Legacy descriptors without a budget
or pinned provenance validate as packages but cannot emit a deployable submit plan.
New applications must also freeze the complete six-axis `stack` signature and
`validation.criterion_version`. The record stores the normalized signature after
external binding platform values are applied.

## Resource binding and budget

New scaffolds use `unconfigured` and region `0`; choose the real enabled profile,
region and queue before doctor or submission. Keep reusable application metadata
separate from deployment selection with an optional external binding file:

```bash
cp examples/binding.example.json /private/binding.json
# Edit its scnet fields and authorized budget; region 0 is a blocked placeholder.
python3 scripts/scnet_app.py plan ../scnet-myapp --binding /private/binding.json --scnet-hpc /absolute/scnet-hpc --remote-dir /absolute/remote/fresh-run
```

The file requires exactly `scnet` and `budget`. It overrides those objects for the
current command without changing app.json. `validate`, `doctor`, `plan` and `record`
accept the same `--binding` option. The plan expands the selected target explicitly.
Credentials still belong only to scnet-hpc.

On native PowerShell use `Copy-Item` instead of `cp`, `python`/`py -3` instead of
`python3`, and actual Windows paths for local files. Remote paths remain absolute
POSIX paths. The external binding file is user-owned deployment configuration.

Budgets cap requested nodes, total CPUs, DCUs per node and walltime **per job**.
Over-budget requests produce `submit: null` with reasons. These checks do not reserve
quota, enforce cumulative retries, know prices or stop jobs that another tool
submits. Live permissions/quota, actual scheduling limits and explicit cancellation
remain the infrastructure's responsibility. Missing site-required memory/QoS/task
parameters still need an explicit adapter extension before deployment.

## Record collected artifacts

```bash
python3 scripts/scnet_app.py record ../scnet-myapp --results ./collected --run-id pilot-001 --artifacts metrics.json raw-output.dat scheduler.out --job-state succeeded
```

List every raw output/log needed for review, not just the final scalar. Numeric
check files are automatically included. Paths must be relative files without
symlinks or traversal. `record` creates a new directory under
`APP/.private/evidence/RUN_ID/`; existing run IDs are refused. It copies the selected
artifacts, hashes sources and results, evaluates numeric checks, then runs the
checker against the private copy in that run directory. Original collected files
are not passed to the checker. Changes to source or snapshot inputs cause failure.

The record retains checker stdout/stderr, failures and checker timeouts.
`record` exits nonzero when acceptance fails or requested platform confirmation
is unconfirmed; it still saves the record. Missing numeric outputs are recorded
as failed checks when the explicitly listed logs/artifacts are available. Use
`--checker-timeout` (1–3600 seconds, default 300). A failed/cancelled/job-timeout/
budget-stopped declaration skips the checker and saves failure evidence.
`wait_timeout` means polling stopped and the job may still run; it is distinct
from terminal `job_timeout`. Local artifact checks may still run after a wait
timeout, but no scheduler success is inferred. No recording command cancels a job.

## Independently check the SCNet job

```bash
python3 scripts/scnet_app.py record ../scnet-myapp --results ./collected --run-id pilot-002 --artifacts metrics.json raw-output.dat scheduler.out --binding /private/binding.json --scnet-hpc /absolute/scnet-hpc --job-id JOB_ID --remote-dir /absolute/remote/fresh-run
```

With `--job-id`, record invokes only the canonical CLI's read-only
`--details job JOB_ID`. `scheduler: passed` requires matching job ID, queue, work
directory, nodes, CPUs and DCUs, confirmed COMPLETED state and a reported successful
exit. Missing facts, API errors or pending accounting stay `unconfirmed`; they do
not become success from the supplied `--job-state`. No private node/account data is
exported automatically. Without successful platform checking, source is
`self_reported`; otherwise it is `scnet_job_checked`.

Platform state checking does not establish that local outputs came from that job,
that its software/environment matches the current application, or that a Hygon
device executed the workload. Preserve the private submit/transfer manifest and
runtime logs to review that linkage. `verification` reports **correctness**,
**scheduler**, **runtime** and **source** separately. `runtime` remains `not_assessed`
and `compute_verified` remains false in v0.2; there is no automatic hardware
certification path. Hygon Z100 DCU probes and application correctness need their
own compute-node evidence and review.

## Re-read and publish evidence

`validate` and `plan` re-read records without executing checkers or contacting SCNet.
Source/binding changes count as `stale_evidence`. Changed checksums, missing/changed
snapshot files or inconsistent recomputed numeric verdicts count as
`invalid_evidence`. The summary uses the latest valid current record, including a
failed one, rather than hiding a regression behind an older pass.

Records are append-only by convention and refuse overwrites. Checksums detect
ordinary edits; they are not signatures and cannot prevent an owner rewriting both
data and checksums. Application checks cannot establish their own independent
authority merely by setting a flag. Keep reviewer-approved references and checker
code outside the adaptation's tuning loop when an independent acceptance is needed.

Raw artifacts and records are private and gitignored. Free-text fields, module
names and logs can contain paths, identities or secrets; a field allowlist does not
sanitize their contents. Publish a separately reviewed compatibility summary with
versions, case/reference, environment, scope and verdicts, keeping raw job/path and
artifact links in private records.

## Design reference

ScienceFlow's separation of evaluator facts, admission policy and artifact identity
informed this small contract. Its research-worker runtime, memory, GPU leasing and
dependency stack are not dependencies of scnet-app. References were reviewed at
commit `d38150de76b45a0992bcfe175957d08004b7319a`:
[GateService](https://github.com/huawei-noah/noah-research/blob/d38150de76b45a0992bcfe175957d08004b7319a/ScienceFlow/scienceflow/gates/service.py),
[artifact evidence](https://github.com/huawei-noah/noah-research/blob/d38150de76b45a0992bcfe175957d08004b7319a/ScienceFlow/scienceflow/solver/lnr/global_merge/candidate_evidence.py).
The operational reference remains [scnet-hashcat](hashcat-reference.md).
