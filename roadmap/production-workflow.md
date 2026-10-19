# Production workflow

## Goal

Given a public source repository, source archive, existing installation, module,
or CPU application that also needs a DCU port, produce a standard skill
repository, an optional SCNet runtime package, a clean-install check and a
private evidence record.

The workflow retries within an authorized budget, changes strategy when evidence
shows that the current strategy is wrong, and stops with a concrete blocker when
it cannot proceed safely.

## State machine

```text
intake -> inspect -> classify -> plan -> cpu_build -> cpu_validate
                                      |
                                      +-> dcu_probe -> dcu_port -> dcu_validate
                                      |
                                      +-> package -> clean_install -> release
```

`dcu_*` is required for a DCU target and optional for a CPU-only target.
`package` and `release` are blocked until correctness, runtime and packaging
gates pass.

Each state writes an immutable attempt directory:

```text
.private/workflow/
  state.json
  attempts/0001/
    plan.json
    commands.json
    stdout.log
    stderr.log
    result.json
    evidence/
    failure.json
```

Existing attempts are never overwritten. A resumed run reads `state.json` and
continues from the latest valid state.

## Strategy selection

| Input or property | Initial strategy |
| --- | --- |
| Native executable and short deterministic input | CPU quick-build |
| CMake/Make/Autotools project with a CPU oracle | CPU build, then optional DCU port |
| HIP/CUDA/backend code already present | Probe target runtime before rebuilding |
| Scientific solver without a backend seam | CPU oracle plus DCU porting plan; no support claim |
| Large or service-shaped installation | B/C shape review before A-level packaging |

Hashcat, GROMACS, CFD examples and other applications are candidates for
reference status. None is privileged until it demonstrates that the workflow is
reusable across build, validation, packaging and evidence stages.

## Retry and stop rules

Every failure is classified before another attempt:

- `retry_same`: transient scheduler, transport or filesystem failure;
- `change_strategy`: build-system, dependency or packaging strategy is wrong;
- `needs_porting`: the CPU result is valid but the accelerator path is absent or incorrect;
- `needs_user_decision`: license, input, budget, target or package shape is unclear;
- `unsupported`: target capability or required dependency is unavailable.

Retries require a fresh run ID and remote directory. A timeout does not imply
success or cancellation. The workflow stops when the authorized attempt or
resource budget is exhausted, a user decision is required, or the target is
known to be unsupported.

## Evidence layers

Keep these claims separate:

1. source and license provenance;
2. CPU build and correctness;
3. target runtime and device participation;
4. scientific or functional acceptance;
5. scheduler/accounting success;
6. package relocation and clean-install behavior;
7. performance and scaling.

Passing one layer never substitutes for another. A partial kernel or device
enumeration is not a full application support claim.

## Completion

An application is deliverable only when the generated skill validates, the
selected CPU/DCU correctness checks pass, runtime/device evidence matches the
accepted stack when applicable, package naming and layout pass, clean-install
and idempotency checks pass, and the compatibility report states tested scope
and untested boundaries.

Otherwise the workflow emits a blocked report with failed attempts and the next
decision required.
