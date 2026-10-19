# ScienceFlow integration notes

This directory records an optional integration boundary for
[Huawei Noah's Ark Lab ScienceFlow](https://github.com/huawei-noah/noah-research/tree/master/ScienceFlow).
It does not vendor the upstream repository or its Python environment.

## Why this is a contrib integration

ScienceFlow provides useful patterns for long-horizon execution:

- recoverable executable workspaces;
- stage gates with normalized evidence;
- re-anchoring and redirecting after validation;
- resource-aware execution control.

Those ideas map naturally to `scnet-app` workflow attempts, evidence records and
retry classification. The core `scnet-app` contract remains authoritative for
SCNet resource binding, package layout, target-node evidence and release gates.

## Upstream and license

- Upstream repository: `huawei-noah/noah-research`
- Subdirectory: `ScienceFlow`
- Reference commit reviewed: `d38150de76b45a0992bcfe175957d08004b7319a`
- License: MIT; see [LICENSE](LICENSE)
- Review date: 2026-10-19

The ScienceFlow subtree's MIT license permits use, copying, modification,
merging, publication, distribution, sublicensing and sale, provided the
copyright and permission notice remain with copies or substantial portions and
the warranty disclaimer is retained.

This permission applies to the ScienceFlow code under that license. It does not
automatically relicense dependencies, model weights, datasets, Git-pinned
projects or external services.

## Dependency boundary

The upstream documentation requires Python 3.11+ and `uv`, uses a locked
environment, includes Git-pinned dependencies and defaults PyTorch to a CUDA
12.8 index. These assumptions are not copied into `scnet-app` runtime packages.
Any future adapter must inspect the selected target stack, dependency licenses,
network requirements and package size before choosing A, B or C delivery.

## Planned adapter boundary

| ScienceFlow concept | scnet-app concept |
| --- | --- |
| executable workspace | `.private/workflow` attempt directory |
| Stage Gate | level-A/application acceptance gate |
| Evaluator evidence | structured result/runtime evidence |
| resource-aware control | SCNet binding, budget and scheduler facts |
| resume/redirect | retry classification and explicit strategy change |

The adapter must not copy credentials, private workspaces, raw scheduler logs
or upstream dependency environments into a public skill repository.
