# Reference application rubric

No application is a permanent benchmark by default. A candidate is promoted
only after it exercises the reusable parts of the production workflow.

Score each candidate from 0 to 2:

| Dimension | 0 | 1 | 2 |
| --- | --- | --- | --- |
| CPU quick path | unavailable | manual | reproducible |
| DCU/runtime path | absent | partial probe | target-node evidence |
| Correctness | ad hoc | functional only | deterministic or numerical oracle |
| Packaging | custom | partial | standard A/B/C shape |
| Failure semantics | ambiguous | some nonzero paths | audited and recoverable |
| Evidence | logs only | mixed records | bound, structured and reviewable |
| Reusability | app-specific | some templates | representative of a class |
| Resource cost | high | moderate | short bounded validation |

Promotion requires no zero in correctness, evidence or failure semantics, at
least 12/18 overall, documented untested boundaries, and a second application
or fixture that reuses the workflow without bespoke core-gate changes.

The current hashcat repository remains a useful operational candidate. It is
not marked as the universal scientific benchmark until this review is complete.
