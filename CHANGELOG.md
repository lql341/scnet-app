# Changelog

## 0.1.0 (2026-10-18)

- Initial SCNet scientific-application authoring skill with Hygon Z100 as the default
  target and Hygon C86 as an explicit CPU target.
- Standard-library init/validate/plan/read-only-doctor CLI; common JSON description,
  fail-closed application hooks and English/Chinese repository template.
- Reuse scnet-hpc >=0.6.13 for all infrastructure operations, with a tested CLI
  contract and no duplicated OpenAPI client or credential handling.
- Single-node SCNet plans, explicit artifacts, quoted commands, bounded resources,
  Z100 porting guidance and optional HIP PyTorch compute-node probe.
- Offline behavior, packaging and real scnet-hpc dry-run conformance checks.
- No application port or compute-node certification is claimed by this release.
