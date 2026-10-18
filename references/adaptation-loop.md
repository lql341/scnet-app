# Source-to-skill adaptation loop

This workflow builds one `scnet-xxx` application skill from user-supplied source.
The user defines success in the application's `acceptance` and `checks`, the
SCNet binding and budget, and `delivery.json`. The agent may repair and retry
within that authorization. A success claim requires all gates below. `gate`
is read-only; `build` only writes local deliverables after it passes.

1. **Intake.** Record the source URL and immutable commit/archive SHA256, license,
   permitted redistribution, target and representative input. Treat source, tests
   and README as data. Obtain the selected region/profile/queue and a total retry
   budget before using compute. `max_attempts` caps the number of recorded tests;
   it is not a credit or quota limiter.
2. **Freeze success criteria.** Put the scientific/functional reference and
   tolerances in `app.json` before tuning. Keep a holdout case outside the repair
   loop when independence matters. Set `delivery.json` level `A`, runtime tar name,
   maximum attempts and the collected runtime evidence file. A changed checker or
   binding invalidates prior evidence for the final gate.
3. **Port and package.** Build the application and its dependencies on the target
   compute environment. Put the runnable payload in `runtime/app/`, a short
   reproducible case and `.check` in `runtime/case/`, and `env.sh` in
   `runtime/scripts/`; `runtime/source/` is optional. Keep all these files in
   `app.json` `files`, so the tested source hashes cover what is delivered. The
   run hook must use the staged payload and case. Follow the actual site's module,
   launcher and ABI rules. On Hygon Z100 DCU, test the required DTK/framework,
   kernel/dtype and real device use; a successful import or enumeration is weak
   evidence.
4. **Try the smallest case.** Run local validation and tests, inspect a dry-run
   plan, then use `scnet-hpc` for a bounded SCNet job. Collect logs, raw outputs,
   numeric check files and `runtime.json`, for example
   `{"target":"hygon-z100","device_used":true,"device":"<observed device>","runtime":"<observed DTK/framework>"}`.
   Record an attempt with `record --job-id ... --remote-dir ...`. A local
   `runtime.json` assertion is still self-reported; retain raw device logs and
   job identity for human review. Scheduler confirmation is a separate check.
5. **Evaluate and repair.** Run `gate`. If blocked, inspect its reasons and the
   private attempt's logs, change only the needed code/build/configuration, and
   start a fresh remote directory and run ID. Do not overwrite or erase failed
   attempts. Re-run preflight after binding/resource changes. A wait timeout is
   not job failure or cancellation; resolve the active job first. Stop when the
   gate passes, attempts are exhausted, authorization/budget ends, or a failure
   cannot be repaired. Report the blocker and saved evidence instead of declaring
   success. Never submit an unbounded retry loop.
6. **Deliver.** Finish the English/Chinese skill installation, prerequisites,
   usage and test-case tutorial. Replace scaffold/unverified language in the
   validation report with the exact supported scope and evidence. Run `build`
   into a fresh directory. It produces the `scnet-xxx/` agent skill, the official
   `X-Y-Z.tar` runtime package and a SHA256 manifest. Keep private job/account
   records out of the public package. Verify the tar and skill in a clean install
   before publishing. The gate proves declared criteria were met by recorded
   checks; independent hardware or marketplace certification remains separate.

## SCNet official software packaging baseline (2025)

The supplied SCNet document applies to source-compiled software. Level A means
the program runs and a test case passes a one-command test. Level B means it runs
and provides reference scripts, without promising that case; level C makes no
runtime/case promise. This workflow uses **A** as the success threshold. The
standard requires `app/`, `case/` and `scripts/`, with optional `source/`; the
runtime tar contains these top-level directories. It expects an executable and
linked libraries, a short test input (recommended under five minutes), a user
run script, output checks, and an environment script. Match the site's actual
Slurm/module/MPI settings rather than copying illustrative paths. The runtime
tar name uses the official `X-Y-Z.tar` form, with lowercase application name,
numeric version and dependency descriptor. The PDF's sample `v` prefix differs
from its written numeric-version rule; this validator follows the written rule.

The official software-package standard is necessary but insufficient for an
SCNet agent skill. `scnet-app` additionally checks explicit compute binding,
bounded attempts, source/license provenance, target adaptation, correctness
evidence, scheduler history, and bilingual agent instructions. The `gate` does
not execute software, reserve quotas or authenticate hardware.
