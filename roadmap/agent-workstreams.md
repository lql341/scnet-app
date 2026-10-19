# Agent workstreams

The workstreams share contracts and evidence formats, not mutable private job
records.

## Wave 1: workflow foundation

### A. Orchestrator and recovery

Implement the intake/classify/plan/build/validate/package/release state machine.
Persist immutable attempts, classify failures and resume from the last valid
state.

Acceptance: interrupted runs resume without overwriting evidence; retry and
resource budgets are enforced; every terminal state is `passed`, `blocked` or
`failed` with a reason.

### B. CPU quick-build adapters

Add conservative detectors and adapters for CMake, Make, Autotools,
Python/Go/Rust and existing binaries. Generate the standard skill skeleton,
minimal smoke case, checker, provenance and package manifest.

Acceptance: a small CPU project produces a validated skill in a clean directory;
malformed input and nonzero exits are tested; dependencies are not silently
guessed.

### C. Gate and evidence runner

Turn the level-A standard file into executable checks and connect runtime/device
evidence to `record` and `gate`. Keep CPU and DCU evidence distinct.

Acceptance: missing entrypoint, bad-input, environment, relocation, idempotency
or device evidence blocks delivery; every check emits a result and evidence path.

## Wave 2: scientific DCU path

### D. Mutable DCU method pack

Use `scientific-dcu-porting` as a maintained method pack, not a fixed authority.
Add target-node probes, CPU oracle templates, backend seams, physical
invariants, lifecycle checks and MPI/device mapping as evidence demonstrates
the need. Tie each revision to a tested target profile and date.

Acceptance: the CPU oracle remains runnable; CPU fallback is not accepted as a
DCU pass; unverified DTK capabilities remain explicitly unverified.

### E. Candidate reference applications

Run the same workflow on hashcat, GROMACS, a small CFD/PDE example and other
practical candidates. Compare them with the rubric rather than promoting
hashcat by default.

Acceptance: each candidate has build, correctness, packaging and evidence
results; a promotion decision records strengths, limits and scope.

## Wave 3: production hardening

### F. Matrix and version governance

Add a versioned matrix schema, lookup commands, migration tests and status
semantics for `reference`, `validated`, `blocked` and `unverified`.

### G. B/C package shapes

Define package contracts for module/image and service/MCP/API applications.
Keep A-level tar behavior backward compatible and fail closed for unsupported
shapes.

### H. Release and supply chain

Add deterministic build checks, dependency/license manifests, clean-install
replays, compatibility reports, tags and rollback metadata.

## Scheduling rule

Wave 1 must be stable before application promotion. Wave 2 can use hashcat as
the first integration target, but the workflow must remain neutral. GROMACS or
a CFD application may replace it as the reference after rubric review. MinerU
remains a B/C design candidate until its package shape is fixed.
