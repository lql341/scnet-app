---
name: __APP_NAME__
description: Prepare and run __APP_NAME__ scientific workloads on SCNet with application-specific correctness checks.
---

# __APP_NAME__

Upstream: __UPSTREAM__. Intended target: `__TARGET__`.
This generated application is unverified. Implement its run/result-check hooks and
acceptance criteria before requesting a compute allocation.
Follow the source-to-skill process in references/adaptation-loop.md. Complete
delivery.json and the official runtime/app, runtime/case and runtime/scripts
package. Preserve each failed attempt and stop at the authorized retry limit.
Pin provenance, declare authorized per-job budget caps and select the actual SCNet
binding. Region 0/unconfigured defaults do not identify an enabled deployment.

Read `app.json` for the SCNet target, six-axis stack, prerequisites, budget,
environment, artifact list and hooks.
Run `python3 scripts/doctor.py` before first use. It is an offline, non-secret
check: report one missing category at a time, never request AK/SK or private keys
in chat, and do not claim remote readiness from a local pass. Follow
references/first-use.md and `scripts/check_contract.py`.
Use scnet-hpc for credentials, live resources, uploads, submit, wait, logs and cancel.
Do not create a second OpenAPI client or credential store. Follow the English and
Chinese README for installation/prerequisites and use the scnet-app planner when
available. Offline planning needs no local accelerator.

Read references/cluster-integration.md before deployment: bind the region/queue
and resource budget, follow Slurm allocation and site packaging policy, and stage
versioned dependencies explicitly. Use scnet-hashcat as an operational reference;
retain this application's own correctness criterion and execution scope.

Run only on the selected SCNet compute nodes. Verify the actual device/runtime;
do not silently execute an accelerator workload on CPU. Capture raw private logs,
exit status and application-specific numerical/functional evidence. Scheduler
completion, import success and device enumeration alone are not correctness proof.

Pass resource preflight before mutations, submit once, and preserve job/region/run
directory references. A waiting timeout does not cancel a job. Keep all expected
rank outcomes when adding parallel execution. Publish sanitized compatibility
reports; keep credentials, account paths, job IDs and recovered/private data private.

Read `references/prerequisites.md` and `references/validation.md` to record what was actually verified. Default
documentation is English; respond in the user's language.
For collected artifacts, follow references/verification.md and scnet-app record.
Keep raw records private; distinguish local correctness, platform job checking and
hardware/runtime evidence. A self-reported state is not platform confirmation.
