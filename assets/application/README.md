# __APP_NAME__

English | [中文](README_CN.md)

Version: 0.1.0. Upstream: __UPSTREAM__. Intended target: `__TARGET__`.
Status: scaffold; no application or compute-node compatibility is claimed.

## Install and prerequisites

Copy this complete skill into your agent's documented skill directory. After
publishing your application repository, replace this paragraph with its exact
one-sentence install prompt and verify that installation in a clean directory.
The generated repository has not been published automatically.

Local Python 3.8+ and scnet-hpc >=0.6.13 provide orchestration. Real execution needs
an SCNet account with the selected region/queue enabled, balance/quota, shared
writable storage and a compatible application/DTK environment on compute nodes.
Reuse scnet-hpc credentials; do not store secrets in app.json. Local installation
does not install the upstream application or open compute access.

## Adapt and use

1. Inspect the upstream license, build system, dependencies and representative input.
2. Edit app.json: SCNet region/queue, requested resources, modules, explicit file
   list, and an application-specific acceptance condition with reference/tolerance.
3. Implement scripts/run.sh (compute node) and scripts/check.py (local collected
   results). Package all required application code/data in the explicit file list.
4. Use scnet-app validate/plan, then scnet-hpc read-only preflight and submit preview.
   The planner blocks a submit command while stock hooks/criteria remain.
5. Run one bounded SCNet case after implementation. Download explicit result/log
   files, check scheduler accounting and exit status, then run the local checker.
6. Record device/runtime and numerical/functional evidence in references/validation.md.

`results/` is the remote artifact directory. Heavy builds and accelerator probes
belong in scheduled compute allocations. CPU baseline and DCU execution are separate
experiments. The default template supports one node; MPI/fan-out needs an explicit
launcher, expected-rank checks and additional tests before changing that scope.

The template license covers this scaffolding only. Upstream code, models, datasets
and redistributed binaries retain their own licenses.
