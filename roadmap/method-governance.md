# Method governance

`scientific-dcu-porting` is a maintained engineering method, not a permanent
specification. It may change when target-node probes, numerical evidence,
packaging constraints or framework behavior expose a better rule.

Every method change records the observation or failure that motivated it, the
target stack and date, whether the rule is universal/profile-specific/
provisional, affected skills and migration notes, and a regression or fixture
that prevents silent drift.

The method pack must not import CUDA, upstream ROCm or another cluster's
capability claims into DTK. Target-node evidence remains authoritative.

`scnet-app` owns delivery contracts, retry state and release gates. The method
pack owns scientific migration guidance. Application repositories own their
domain-specific oracle and acceptance criteria.
