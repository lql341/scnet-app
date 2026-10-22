# Changelog

## 0.6.0 (2026-10-21)

- Add the mandatory derived-application contract: single entry, first-use
  onboarding, local doctor, shared credential contract, offline dry-run,
  actionable failures and first-use tests.
- Require the same external contract for embedded-adapter and installed-CLI
  application skills.

## 0.5.3 (2026-10-21)

- Update the scnet-hashcat reference pin to the 0.2.3 vendor-manifest release.

## 0.5.2 (2026-10-21)

- Refresh the scnet-hashcat reference to the current single-skill embedded-adapter
  commit and add the vendor-manifest test to the reusable requirements.
- State the exact DCU module/package naming form `<runtime><version>-<target>`.
- Record the skill-role taxonomy: meta, foundation, application entry points and
  porting capability.

## 0.5.1 (2026-10-21)

- Refine the application/scnet-hpc architecture for a single-skill user entry:
  allow a pinned embedded OpenAPI adapter (the scnet-hashcat pattern) or an
  installed scnet-hpc CLI, without requiring users to load two skills.
- Keep the boundary against duplicating the full SSH/scheduler stack or creating
  a second credential store.

## 0.5.0 (2026-10-21)

- Codify the application/entry-point architecture: application skills are
  entry points, `scnet-hpc` is the shared contrib capability, and `scnet-app`
  is the authoring standard.
- Require dependency resolution via `SCNET_HPC_ROOT`, sibling `../scnet-hpc` or
  the installed skill, with a tested minimum version and no vendored transport or
  credential layer for new skills.

## 0.4.6 (2026-10-21)

- Fix Windows local level-A/quick-build execution: prefer Git Bash over WSL,
  pass POSIX relative hook paths, and identify Windows executables by native
  suffix instead of POSIX executable bits.
- Update quick-build tests to assert the actual produced binary name.

## 0.4.5 (2026-10-21)

- Add an MPI/accelerator transport recommendation: prefer OpenMPI+UCX with
  Slurm PMIx, balanced allocation, profile-driven HCA selection and HCOLL
  disabled when it fails or regresses; treat PMPI/OB1 as a fallback and measure
  GPU-aware communication rather than inferring benefit from detection.

## 0.4.4 (2026-10-21)

- Require user-level module/prefix assumptions and explicit blank-account
  probing.
- Distinguish the Linux compute target from a Windows, macOS or Linux local
  agent host; keep remote paths POSIX and local helpers cross-platform.

## 0.4.3 (2026-10-21)

- Add a blank-account baseline: do not assume a maintainer-owned module,
  prefix, modulefile or toolchain; probe the allocated node first.

## 0.4.2 (2026-10-21)

- Distinguish source-built delivery, existing-module validation and minimal
  runtime-probe tracks so mature applications are not forced into the package
  contract.
- Clarify backend evidence levels and version-adaptation guidance for
  module-based applications.

## 0.4.1 (2026-10-19)

- Add a workflow-first production roadmap for turning source or installations
  into validated skill repositories and runtime packages.
- Make reference applications provisional and add a rubric for promoting one
  to benchmark status.
- Add mutable-method governance for scientific DCU porting guidance.
- Add an optional ScienceFlow contrib boundary with upstream attribution,
  MIT-license text and dependency/re-distribution limits.

## 0.4.0 (2026-10-19)

- Add a backward-compatible six-axis stack signature for system, toolchain,
  backend, MPI, framework and SCNet platform identity.
- Add prerequisite/conflict metadata, versioned level-A standard checks and an
  R1 compatibility matrix reference.
- Store normalized stack signatures and fingerprints in private evidence records.
- Validate DCU delivery module/package names against the backend version and target.
- Extend generated application scaffolds with stack, prerequisite and validation
  fields and bilingual prerequisite guidance.

## 0.3.0 (2026-10-18)

- Add a source-to-skill adaptation loop with bounded recorded attempts and a
  read-only delivery gate before building a finished agent skill and runtime tar.
- Treat the SCNet 2025 source-built software packaging standard as the mandatory
  level-A baseline, adding target-runtime evidence, SCNet job confirmation and
  bilingual agent documentation.
- Keep private attempts out of delivery and retain separate correctness,
  scheduler and hardware-certification meanings.

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
