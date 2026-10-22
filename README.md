# scnet-app

English | [中文](README_CN.md)

Version: 0.5.2

A meta-skill for authoring application skills for HPC, AI4S and scientific
workloads on [SCNet](https://www.scnet.cn). `scnet-hpc` is the foundation;
`scnet-*` repositories are application entry points; `scientific-dcu-porting`
is a porting capability. It standardizes **resource binding,
Slurm scheduling, cluster application packaging and result verification** through
a consistent skill scaffold and a reviewable job plan.
[scnet-hpc](https://github.com/lql341/scnet-hpc) supplies the infrastructure;
the application supplies its scientific logic and correctness checks.
Hardware/runtime compatibility, including **Hygon Z100 DCU / DTK**, is one part
of this integration workflow.

`scnet-hashcat` is the current operational candidate for packaging and evidence,
not a permanent scientific benchmark. See the [reference application rubric](roadmap/reference-application-rubric.md)
and [production roadmap](roadmap/README.md) before promoting any application.

## Install with one sentence

> Use `$skill-installer` to install `scnet-app` from the root of GitHub repository `lql341/scnet-app` (path `.`, ref `main`), name it `scnet-app`, preserve an existing destination, run `scripts/scnet_app.py --help` with Python 3 from the installed directory, and report the absolute installation path; do not configure credentials or allocate compute during installation.

For other SKILL.md hosts, install the whole repository root under the host's
skill directory and refresh discovery. Codex's normal destination is
`$CODEX_HOME/skills/scnet-app` or `~/.codex/skills/scnet-app`; invoke on the next turn.
Cloning provides CLI access but does not itself register a skill:

```bash
git clone https://github.com/lql341/scnet-app.git
cd scnet-app
python3 scripts/scnet_app.py --help
```

Local runtime: Python 3.8+ standard library. Windows uses `python` or `py -3`.
No local GPU, DTK, PyTorch, account secret or pip package is needed to scaffold.
The optional PyTorch probe has its own remote framework prerequisite.

## Ask the agent to adapt an application

> Use `$scnet-app` to integrate the scientific application I provide with SCNet compute: bind its region/queue and resource budget, follow Slurm scheduling and target-cluster packaging requirements, use the current operational candidate mappings, and check hardware/runtime compatibility including Hygon Z100 DCU when selected. Deliver English/Chinese install and use instructions, a real correctness check and a minimal single-node smoke plan. Keep compatibility unverified until compute-node evidence exists; use only the authorized compute budget.

For a finished application rather than a scaffold, say: "Use `$scnet-app` on this
source revision and my acceptance case; within the SCNet region/queue, total
budget and maximum attempts I specify, repair and retest until the level-A gate
passes, then deliver the installable `scnet-xxx` skill, SCNet runtime tar,
English/Chinese installation and usage tutorial, runnable test case and evidence
manifest; if a gate remains blocked, report the failed attempts and stop."

Give the agent the upstream repository/revision, a representative input/reference,
known environment constraints and your compute budget when a real test is wanted.
For repeated adaptation through a finished `scnet-xxx` skill, specify the exact
success criterion and maximum authorized attempts. Follow the
[source-to-skill loop](references/adaptation-loop.md). The official SCNet
source-built software packaging standard is the mandatory baseline; target
compatibility and agent usability add further gates.
Existing application repositories can adopt the contract in place; init only creates
new repositories and never overwrites one.

The evolving source-to-skill production plan is maintained under
[roadmap/](roadmap/README.md). Optional external workflow integrations are
documented under [contrib/](contrib/README.md).

## Minimal workflow

Replace OWNER/PROJECT with the real upstream and the quoted directories with actual
paths. Run these from the installed scnet-app root:

```bash
python3 scripts/scnet_app.py init scnet-myapp --output ../scnet-myapp --upstream https://github.com/OWNER/PROJECT
python3 scripts/scnet_app.py validate ../scnet-myapp
python3 scripts/scnet_app.py plan ../scnet-myapp --binding "/private/binding.json" --scnet-hpc "/absolute/scnet-hpc" --remote-dir "/absolute/remote/fresh-run"
```

For a small CMake or Make CPU source tree, the first vertical-slice workflow can
build a clean application skill and local runtime package without a cluster:

```bash
python3 scripts/scnet_app.py quick-build ./source --output ./scnet-myapp \
  --name scnet-myapp --upstream https://example.org/project
python3 scripts/scnet_app.py level-a ./scnet-myapp --output ./level-a.json
python3 scripts/scnet_app.py intake ./scnet-myapp
python3 scripts/scnet_app.py run ./scnet-myapp
```

`quick-build` supports conservative CMake/Make detection only; it does not guess
dependencies or claim compute-node compatibility. `level-a` executes the eight
local package checks and keeps accelerator evidence declarative. The workflow
commands persist resumable state under `.private/workflow/` and preserve failed
attempts.

For an arbitrary input, inspect it before selecting an adapter:

```bash
python3 scripts/scnet_app.py inspect-source /path/to/source-or-package \
  --output ./intake.json
```

The inspector safely accepts source directories, tar/zip archives, installed
layouts and existing skill repositories. It records a deterministic tree hash,
build markers, license-file candidates and the next supported action; it does
not execute untrusted build scripts.

The result is a scaffold, not a ported application. Implement the run/check hooks,
human-readable acceptance and structured checks. Pin the upstream commit/archive
hash and license in provenance. New scaffolds have no implicit cluster selection:
configure app.json or copy and edit [binding.example.json](examples/binding.example.json)
at the binding path above with your real profile/region/queue and authorized budget.
The planner withholds submit while these facts/hooks are missing or a request
exceeds its per-job budget. Existing v1 descriptors still load; new fields are additive.

Then read [the contract](references/contract.md), run the read-only preflight:

```bash
python3 scripts/scnet_app.py doctor ../scnet-myapp --binding "/private/binding.json" --scnet-hpc "/absolute/scnet-hpc"
```

Review live account/queue/quota and the generated scnet-hpc `--dry-run` preview.
When the implementation and authorized budget are ready, use scnet-hpc for the
planned transfer/submission, bounded wait, status, explicit artifact downloads and
cancellation. This authoring CLI executes no remote mutation. `plan` does not
reserve the remote path: select a new dedicated directory for every run.

After collecting outputs, record a private local acceptance result:

```bash
python3 scripts/scnet_app.py record ../scnet-myapp --results ./collected --run-id pilot-001 --artifacts metrics.json runtime.json raw-output.dat scheduler.out --binding "/private/binding.json"
```

Replace artifact names with actual raw outputs/logs. The record freezes hashes,
checks numeric criteria before the checker, and rejects input changes. Add
`--job-id JOB_ID --remote-dir /absolute/remote/fresh-run --scnet-hpc /absolute/scnet-hpc`
to check the platform's job facts through its read-only CLI. Local correctness,
scheduler confirmation and hardware/runtime evidence are separate; the current release keeps
`compute_verified: false`. See [acceptance and evidence](references/verification.md)
for formats, failure/timeout handling, source labels and privacy limits.

## Prerequisites by stage

| Stage | Required |
| --- | --- |
| init / validate | Local Python 3.8+ and this complete repository |
| plan | Also a local scnet-hpc >=0.6.13; adapter tested with 0.6.13; no credentials/network |
| doctor | Also SCNet access, enabled region/queue and scnet-hpc credentials |
| record | Authored checks, trusted local checker and explicit collected artifacts; optional --job-id also needs the doctor prerequisites |
| Real application job | Account balance/quota, staged input/dependencies, shared writable storage, compatible application/DTK environment and requested devices |
| gate / build | Completed level-A `runtime/app`, `runtime/case`, `runtime/scripts`, bilingual instructions, accepted SCNet job and target runtime record; `build` needs a fresh local output directory |

## From source to finished skill

The generated `delivery.json` sets the level-A tar name, attempt limit and required
runtime evidence file. Define the application's acceptance tests in `app.json`.
Port the user-supplied source into `runtime/app/`, include a runnable short test in
`runtime/case/testcase/`, `runtime/case/.check`, a site-adjusted `.slurm` example
and `runtime/scripts/env.sh`. Stage every runtime file in `app.json` `files`, so
the accepted job's source hashes cover the delivered payload. The optional
`runtime/source/` holds redistributable source and build instructions.

After each bounded test, use `record` to keep the result and failure logs. Then:

```bash
python3 scripts/scnet_app.py gate ../scnet-myapp --binding /private/binding.json
python3 scripts/scnet_app.py build ../scnet-myapp --binding /private/binding.json --output /fresh/scnet-myapp-delivery
```

`gate` reports concrete blockers, the count of recorded attempts and whether a
retry remains. It requires the latest current correctness record, matching SCNet
job history, target-matched collected runtime evidence, level-A package layout,
staged package files and completed bilingual guidance. `build` refuses a failed
gate and creates a `scnet-xxx/` skill directory, `X-Y-Z.tar` runtime package and
SHA256 manifest. This is a local delivery gate, not independent hardware or
marketplace certification. It never submits or retries jobs by itself. Use a
fresh run ID and remote directory for each authorized attempt; resolve wait
timeouts before submitting another job.

Set the scnet-hpc location with `--scnet-hpc`, `SCNET_HPC_ROOT`, or use the standard
Codex skill installation directory. Credentials are handled only by scnet-hpc's
setup/environment/OS store. No AK/SK, token, SSH key or endpoint goes into app.json.
Local installation does not install the scientific application or activate SCNet.

## Integration contract and current scope

| Area | Required application behavior |
| --- | --- |
| SCNet resource binding | Explicit region/profile/queue, live account access and quota, bounded CPU/DCU/time requests |
| Slurm scheduling | Use the infrastructure submission path; respect allocation and device visibility; preserve exit status, job identity and accounting |
| Cluster packaging | Explicit staged files, reproducible dependency/build instructions, site modules, compute-node ABI, separate software/input/run/result paths |
| Correctness and evidence | Collect logs and declared results; check scientific/functional acceptance separately from scheduler success |
| Hardware/runtime compatibility | Check the selected target, including Hygon Z100 DCU / DTK; retain actual device and runtime evidence |

Read the [cluster integration requirements](references/cluster-integration.md)
and [scnet-hashcat reference](references/hashcat-reference.md). These are this
project's integration conventions, applied with the target site's actual policies;
they are not a claim of universal SCNet packaging certification. `validate` checks
the application descriptor and staged file paths, not every site/runtime policy.

The reusable OpenFOAM application skill is maintained separately in
[scnet-openfoam](https://github.com/lql341/scnet-openfoam); this meta-skill keeps
the SCNet application contract and integration boundaries, not Kunshan run paths
or raw job logs.

The scaffold starts with one node, eight **total** CPUs, one DCU and three minutes,
with matching per-job budget caps. Region 0 / unconfigured profile/queue block
deployment until explicitly selected. Hardware profile hints are not live availability.
`--target hygon-c86` explicitly creates a CPU application with zero DCUs and CPU
budget caps. Live scheduler/profile facts take precedence over hints.

The current contract standardizes **single-node** pilots. MPI, distributed fan-out, arrays, automatic
CUDA conversion and remote software deployment are not implemented. No application
has been certified by this scaffold. See [Hygon Z100 DCU guidance](references/hygon-z100.md)
for ABI/toolchain, operator/dtype, memory and numerical verification boundaries.

```text
SKILL.md / agents/      Authoring instructions and UI metadata
schema/app.schema.json Application description v1
scripts/scnet_app.py   init / validate / plan / doctor / record / gate / build
scripts/scnet_delivery.py Official-package and application-skill delivery gate
scripts/scnet_evidence.py Private snapshots, acceptance and provenance checks
examples/             Explicit environment binding and resource caps
assets/application/   Application repository template
assets/probes/        Optional compute-node framework probe
targets/              Versioned hardware/profile hints, not live evidence
references/           English and Chinese contract/porting instructions
tests/                Offline behavior and scnet-hpc CLI conformance
```

```bash
python3 -m unittest discover -s tests -v
python3 scripts/validate_repo.py
```

Current verification includes regression tests for budgets, binding, artifact/checker
integrity, private records and job confirmation, plus a real scnet-hpc offline
submit preview without credentials. Earlier v0.1 read-only doctor/resource-summary
access succeeded. No compute allocation or application adaptation was performed
for this release. CI runs Ubuntu Python
3.8/3.12 and Windows Python 3.12; inspect its result for the current revision.

MIT for the scaffold. Upstream applications/models/data retain their own licenses.
