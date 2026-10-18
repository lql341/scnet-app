---
name: __APP_NAME__
description: Prepare and run __APP_NAME__ scientific workloads on SCNet with application-specific correctness checks.
---

# __APP_NAME__

Upstream: __UPSTREAM__. Intended target: `__TARGET__`.
This generated application is unverified. Implement its run/result-check hooks and
acceptance criteria before requesting a compute allocation.

Read `app.json` for the SCNet target, budget, environment, artifact list and hooks.
Use scnet-hpc for credentials, live resources, uploads, submit, wait, logs and cancel.
Do not create a second OpenAPI client or credential store. Follow the English and
Chinese README for installation/prerequisites and use the scnet-app planner when
available. Offline planning needs no local accelerator.

Run only on the selected SCNet compute nodes. Verify the actual device/runtime;
do not silently execute an accelerator workload on CPU. Capture raw private logs,
exit status and application-specific numerical/functional evidence. Scheduler
completion, import success and device enumeration alone are not correctness proof.

Pass resource preflight before mutations, submit once, and preserve job/region/run
directory references. A waiting timeout does not cancel a job. Keep all expected
rank outcomes when adding parallel execution. Publish sanitized compatibility
reports; keep credentials, account paths, job IDs and recovered/private data private.

Read `references/validation.md` to record what was actually verified. Default
documentation is English; respond in the user's language.
