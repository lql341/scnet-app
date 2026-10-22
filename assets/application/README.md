# __APP_NAME__

English | [中文](README_CN.md)

Version: 0.1.0. Upstream: __UPSTREAM__. Intended target: `__TARGET__`.
Status: scaffold; no application or compute-node compatibility is claimed.

Follow [the adaptation loop](references/adaptation-loop.md) to turn supplied
source into a verified level-A software package and `scnet-xxx` skill. Complete
delivery.json, runtime/app/, runtime/case/ and runtime/scripts/. After every
recorded test, run scnet-app `gate`; `build` creates the skill and official tar
only after all declared checks pass. Replace this scaffold text with the tested
installation, prerequisites, one-command test and usage tutorial.

## Install and prerequisites

Copy this complete skill into your agent's documented skill directory. After
publishing your application repository, replace this paragraph with its exact
one-sentence install prompt and verify that installation in a clean directory.
The generated repository has not been published automatically.

Run `python3 scripts/doctor.py --json` for the offline first-use state and
`python3 scripts/check_contract.py` to verify the generated onboarding files.
The bridge doctor checks environment credentials and app.json region/queue only;
it never claims remote activation or module deployment.

Local Python 3.8+ and scnet-hpc >=0.6.13 provide orchestration. Real execution needs
an SCNet account with the selected region/queue enabled, balance/quota, shared
writable storage and a compatible application/DTK environment on compute nodes.
Reuse scnet-hpc credentials; do not store secrets in app.json. Local installation
does not install the upstream application or open compute access.

## Adapt and use

Follow the [cluster integration checklist](references/cluster-integration.md) for
SCNet resource binding, Slurm scheduling and runtime packaging. The operational
reference is [scnet-hashcat](https://github.com/lql341/scnet-hashcat); use the
new application's own scientific acceptance criterion.

1. Inspect the upstream license, build system, dependencies and representative input.
2. Edit app.json: SCNet region/queue, complete six-axis stack, prerequisites,
   requested resources, modules, explicit file list, pinned provenance
   (revision/license), authorized per-job budget, acceptance and structured
   numeric/hook checks. New region 0/unconfigured values are blocked.
3. Implement scripts/run.sh (compute node) and scripts/check.py (local collected
   results). Package all required application code/data in the explicit file list.
4. Use scnet-app validate/plan, then scnet-hpc read-only preflight and submit preview.
   The planner blocks a submit command while stock hooks/criteria remain.
5. Run one bounded SCNet case after implementation. Download explicit result/log
   files, check scheduler accounting and exit status, then run the local checker.
6. Record stack, device/runtime and numerical/functional evidence in
   references/prerequisites.md and references/validation.md.

Use an external scnet/budget binding when sharing this application across deployments.
After collection, use scnet-app record with explicit raw result/log artifacts;
records and snapshots stay in .private/evidence/. See
[acceptance and evidence](references/verification.md). Local acceptance and optional
platform job checking do not certify hardware compatibility.

`results/` is the remote artifact directory. Heavy builds and accelerator probes
belong in scheduled compute allocations. CPU baseline and DCU execution are separate
experiments. The default template supports one node; MPI/fan-out needs an explicit
launcher, expected-rank checks and additional tests before changing that scope.

The template license covers this scaffolding only. Upstream code, models, datasets
and redistributed binaries retain their own licenses.
