# SCNet application production roadmap

This directory is the maintained development plan for turning a source
repository, source archive, or existing installation into a reproducible
`scnet-xxx` skill repository and runtime package.

The roadmap is workflow-first. `scnet-hashcat` is currently a useful operational
example, but it is not a permanent benchmark or a complete scientific
application standard. Candidate reference applications are evaluated against
the same contract before one is promoted as a benchmark.

## Documents

- [Production workflow](production-workflow.md): the end-to-end state machine,
  retry semantics, evidence boundaries and completion conditions.
- [Agent workstreams](agent-workstreams.md): parallel implementation tracks,
  dependencies, deliverables and acceptance criteria.
- [Reference application rubric](reference-application-rubric.md): how to
  compare hashcat, GROMACS, CFD examples and other candidates.
- [Method governance](method-governance.md): how `scientific-dcu-porting` and
  other guidance are revised from measured evidence instead of treated as
  immutable doctrine.

The roadmap is not a deployment authorization. Every real SCNet job still
requires an explicit user budget, target binding and fresh evidence.
