# Application cluster integration checklist

English | [中文](cluster-integration_CN.md)

Complete this for the selected SCNet deployment before claiming readiness:

- Bind app.json to the enabled region/profile/queue and live quota. Confirm total
  CPUs, DCUs per node and walltime; document required memory/thread/QoS constraints
  and resolve any parameters the current contract cannot express before submission.
- Record the site-approved module/software prefix, exact application/dependency
  versions, source revision, build options, checksums and compute-node ABI/runtime.
  Installing this agent skill does not install the remote software.
- Separate software, inputs, a fresh shared run directory and results/logs. List
  extra staged files/archives in app.json files. Document archive extraction and
  offline dependency preparation; directory recursion is not provided by the planner.
- Run within the Slurm allocation, respect device visibility and thread limits,
  use the site's required job-step launcher and propagate failure. Heavy builds
  belong on scheduled compute resources. Preserve job/region/path for wait/cancel.
- Collect explicit artifacts and logs, confirm accounting/exit status, then run
  this application's checker against its reference. Record untested stages honestly.

See [scnet-app integration requirements](https://github.com/lql341/scnet-app/blob/main/references/cluster-integration.md)
and its [scnet-hashcat benchmark mapping](https://github.com/lql341/scnet-app/blob/main/references/hashcat-reference.md).
The benchmark does not grant multi-node support or certify this application's
scientific results or selected hardware compatibility.
