# Acceptance and private records

English | [中文](verification_CN.md)

Implement app.json checks before collecting evidence. Numeric checks name a JSON
file/key, finite reference and nonnegative absolute/relative tolerances. Hook checks
name a functional criterion; scripts/check.py must exit zero and emit named boolean
verdicts, for example `{"checks":{"structure":true}}`. Keep raw artifacts available
for review and put checker diagnostics on stderr.

Freeze the reference/checker, exact upstream revision or source-archive SHA256,
license and dependency manifest. Declare an authorized per-job budget and an actual
SCNet binding. New scaffolds select no cluster; use app.json or an external binding.

From the installed scnet-app root, replacing all example names/paths:

```bash
python3 scripts/scnet_app.py record /absolute/__APP_NAME__ --results /absolute/collected --run-id pilot-001 --artifacts metrics.json raw-output.dat scheduler.out --binding /private/binding.json
```

record creates a private input snapshot, checks for mutation and retains failure/
timeout logs under this application's .private/evidence/. It refuses existing run
IDs. Optional --job-id/--remote-dir/--scnet-hpc checks platform facts through the
read-only job CLI. Local correctness, scheduler confirmation and runtime evidence
remain distinct; v0.2 does not automatically certify hardware compatibility.

Checksums detect edits but do not make local records tamper-proof. Publish only
a separately reviewed summary; retain private job/input/output provenance.
Detailed formats, limits and upgrade instructions:
[scnet-app verification](https://github.com/lql341/scnet-app/blob/main/references/verification.md).
