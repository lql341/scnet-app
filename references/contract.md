# Application contract v1

English | [中文](contract_CN.md)

The standard is one app.json, a Bash compute hook and a local Python correctness
checker. The schema is [app.schema.json](../schema/app.schema.json); the CLI
checks its used JSON Schema keywords plus path/target semantics. It is not a
general-purpose JSON Schema engine.

Apply the [cluster integration requirements](cluster-integration.md) for resource
binding, Slurm allocation and runtime packaging; use the
[scnet-hashcat mapping](hashcat-reference.md) as an implementation reference.

| Field | Meaning |
| --- | --- |
| schema_version | Integer 1; future incompatible changes require another schema |
| name / upstream | Namespaced skill name and public HTTPS project URL; record the exact source revision in validation notes |
| target | hygon-z100 (DCU) or explicit hygon-c86 (CPU); no automatic fallback |
| scnet | openapi backend, existing cluster profile name, explicit region ID and queue |
| resources | One node, total CPU count, per-node DCUs and positive HH:MM:SS walltime |
| environment | Site modules and optional existing absolute remote modulefiles directory; no guessed universal DTK version |
| stack (v1 extension) | Full system/toolchain/backend/MPI/framework/platform signature; required for new deployable applications |
| prerequisites (v1 extension) | Required modules, conflicts and acquisition guidance; runtime/ABI dependencies stay explicit |
| validation (v1 extension) | Criterion version and required standard suites, with optional device-evidence patterns |
| run | Relative Bash hook executed on the allocated compute node |
| check | Relative Python hook executed locally after result collection; takes a results directory argument |
| files | Explicit relative files staged in addition to app.json/run/check; preserve directory structure |
| acceptance | Application-specific reference, tolerance or functional success condition |
| provenance (optional v1 extension) | Exact upstream commit/source-archive SHA256 and license; required for a deployable plan |
| budget (optional v1 extension) | Per-job max_nodes, max_cpus, max_dcus_per_node and max_walltime; required for a deployable plan |
| checks (optional v1 extension) | Required numeric/hook verdicts and optional holdout metadata; required for record |

Read [prerequisites](prerequisites.md) and [acceptance and evidence](verification.md) for formats, external binding,
private records and v0.1 upgrades. Schema version stays 1; the CLI release is 0.4.1.
Missing new fields do not break loading; deployment facts and checks gate submit
and record respectively.

Unknown fields are rejected so credentials/endpoints cannot become an alternative
configuration channel. Use scnet-hpc for credentials and live resources. Artifact
paths cannot escape the application root; missing files and escaping symlinks fail.
Package directories or large dependencies as explicit archives and add an application
staging/build procedure; recursive dependency collection is not implemented.

New applications should use the six-axis stack signature. The platform axis is
included in evidence but does not change binary ABI naming; the backend version
and product target do. A configured DCU application must include those values in
both `delivery.json.module_name` and `delivery.json.package_name`.

## Hooks

run.sh runs in the remote run directory. It must select the intended device/runtime,
execute the bounded application, put artifacts under results/ and propagate failure.
Do not hide failed pipelines, fall back to CPU, or return 0 after a failed rank.

check.py runs on the driving machine with the collected directory argument. It must
reject missing/malformed artifacts, check actual application results against a
reference and return nonzero when the numerical/functional condition fails. A
"file exists" check alone is rarely a scientific correctness check. Keep any checker
dependencies documented; the authoring CLI itself remains standard-library-only.

The stock hooks carry SCNET_APP_UNIMPLEMENTED and exit 2. The planner withholds a
submit vector until markers/stock criteria are replaced and binding, provenance
and an in-budget resource declaration are ready.
Removing those markers does not certify an implementation. Packaging validation,
API doctor, device probes, numerical correctness and performance are separate stages.

## SCNet bridge

The planner calls no command. It returns argv arrays for read-only preflight,
explicit mkdir/uploads, a scnet-hpc dry-run preview and, when hooks are authored,
a submit command. Pass arrays to subprocess without shell=True. The remote Bash
body quotes directory/module/hook arguments. Keep plans private: they contain
local/remote paths even though no secrets are read.

The bridge uses scnet-hpc >=0.6.13, with conformance tested against 0.6.13. Resolve
its root via --scnet-hpc, SCNET_HPC_ROOT or the Codex skill directory. It never
silently selects SSH or implements its own authentication, token cache or file API.
Application/scnet-hpc releases have independent versions.

Before remote mutation inspect the selected account, live queue and quota against
the plan. Confirm the remote directory is new and dedicated; plan does not reserve
it and upload does not pass --cover. Transfer all declared artifacts before submitting.
Resolve one region, submit once, preserve job ID/directory and poll with a bounded
wait. A wait timeout leaves the job active. Use explicit status/cancel commands.

For collection, list all files through scnet-hpc pagination, download explicit
results and scheduler stdout/stderr, confirm accounting and workload exit status,
then run the local checker. Current scaffolding does not implement a general
collector or automatic submit/wait/cleanup loop. When adding multi-rank execution,
require every expected rank and keep partial artifacts while reporting failure.

## Evidence and publishing

Record upstream revision; actual CPU/DCU architecture, OS/glibc and DTK/framework;
input/reference and tolerance; scheduler/workload status; correctness result; memory,
time and scope. Keep private run/job/node/path details outside public reports.
Classify evidence as profile hint, local packaging, runtime/device probe, application
correctness or performance. Never promote one category to another without a test.

A generated application has its own version/license and bilingual README. Before
publishing it, resolve upstream redistribution rights, supply the real repository's
one-sentence install prompt and verify installation plus a minimal application case.
No generated application repository is uploaded automatically.
record stores private local artifacts and verdicts; optional job checking calls
only scnet-hpc's read-only CLI. Source/result checksums are integrity aids, not
independent hardware attestation. See [verification](verification.md).
