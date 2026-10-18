# Changelog

## 0.2.0 (2026-10-18)

- Add optional v1 fields for numeric/hook checks, pinned source/license and per-job
  CPU/DCU/node/walltime caps; keep legacy packages readable.
- Remove implicit cluster selection from new scaffolds; support external scnet/budget
  binding. Block incomplete or over-budget submission vectors.
- Add private record snapshots, source/result hashes, numeric acceptance, named
  hook verdicts, mutation detection and checker timeout/failure logs.
- Separate local correctness from read-only SCNet job confirmation and runtime
  certification. Keep compute_verified false; do not treat self-reports as proof.
- Revalidate integrity and source/binding scope without rerunning checkers; document
  privacy, scientific holdout choice and compatibility upgrades.
- Incorporate ScienceFlow evaluator/artifact separation lessons while retaining
  scnet-hashcat as the operational reference; add budget/evidence regression tests.

## 0.1.0 (2026-10-18)

- Position the meta-skill around SCNet resource binding, Slurm scheduling, cluster
  packaging and verification; keep Hygon Z100 DCU compatibility as one dimension.
- Add bilingual integration requirements and generated deployment checklists;
  reference scnet-hashcat at a pinned revision as the operational benchmark,
  documenting infrastructure and single-node/multi-node contract differences.
- Describe public scope as SCNet cluster environments; keep site selection in execution configuration.
- Initial SCNet scientific-application authoring skill with Hygon Z100 DCU as the default
  target and Hygon C86 as an explicit CPU target.
- Standard-library init/validate/plan/read-only-doctor CLI; common JSON description,
  fail-closed application hooks and English/Chinese repository template.
- Reuse scnet-hpc >=0.6.13 for all infrastructure operations, with a tested CLI
  contract and no duplicated OpenAPI client or credential handling.
- Single-node SCNet plans, explicit artifacts, quoted commands, bounded resources,
  Hygon Z100 DCU porting guidance and optional HIP PyTorch compute-node probe.
- Offline behavior, packaging and real scnet-hpc dry-run conformance checks.
- No application port or compute-node certification is claimed by this release.
