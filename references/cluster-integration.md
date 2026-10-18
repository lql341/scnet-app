# SCNet cluster integration

English | [中文](cluster-integration_CN.md)

Use this with the [application contract](contract.md) when authoring an application.
It defines this project's delivery conventions. Obtain the selected cluster's
software/module, storage, scheduler and redistribution policies before deployment;
there is no assumed universal SCNet binary package format.

## Resource binding and Slurm

| Application declaration | Infrastructure behavior and review |
| --- | --- |
| scnet.cluster / region / queue | Resolve an existing profile and enabled SCNet region/queue; confirm permission and quota with scnet-hpc doctor/resource-summary |
| resources.nodes | v1 requires one node; allocation alone does not launch work on additional nodes |
| resources.cpus | Total CPU request passed to scnet-hpc --cpus; do not reinterpret it as Slurm --cpus-per-task or a process/thread count |
| resources.dcus_per_node | Passed to scnet-hpc --dcus; site configuration determines the device/GRES mapping and binding |
| resources.walltime | Positive HH:MM:SS passed to --walltime; check the selected queue's actual limit |
| environment and run | Load declared site modules and run the Bash hook inside the allocated compute job, in the dedicated shared run directory |

The application uses the SCNet/scnet-hpc submission path, rather than constructing
a parallel sbatch client. Review the preview against site policy. The descriptor
currently has no memory, account/QoS, task/thread topology or container fields.
If any are required and cannot be supplied by the existing profile/backend, stop
the deployment and explicitly extend the contract/adapter with validation before
claiming support; do not hide missing scheduler requests in shell commands.

The hook must respect allocated device visibility and choose its thread count
within the allocation. Use the site's required srun/MPI launcher for job steps when
applicable; avoid nested allocation/submission. v1 does not provide a generic MPI
launcher. Heavy compilation, benchmarks and accelerator probes require scheduled
compute resources. Never use login nodes for application compute.

Submission success is not job completion. Persist the region, job ID and run path;
submit once, wait for a bounded time and inspect state/accounting and workload exit
status. A polling timeout leaves the job active. Keep explicit status and cancel
instructions. Propagate nonzero exits through wrappers/pipelines and check every
expected rank when adding distributed execution.

Slurm's [sbatch documentation](https://slurm.schedmd.com/sbatch.html) distinguishes
submission from allocation and explains that input files are not staged for the
user. The [srun documentation](https://slurm.schedmd.com/srun.html) describes job
steps and resource binding; the installed version and site configuration govern
the actual launch policy.

## Two packages, one reproducible deployment

The **agent skill package** contains SKILL.md, metadata, bilingual install/use
instructions, app.json, hooks, tests and validation records. Installing it registers
agent instructions; it does not install the scientific software on a cluster.

The **cluster runtime package** contains or references the application build,
dependencies and inputs needed by the compute hook. For each application:

1. Record source revision, patches, licenses, build options, OS/glibc/CPU ABI,
   framework/compiler/MPI and selected accelerator runtime. Pin dependency versions
   and record checksums for distributed archives. Document how to reproduce and
   verify the build using the target site's supported module/package conventions.
2. Prefer an existing validated site module. Otherwise document an approved
   user-owned software prefix and modulefile, or an explicitly supported container
   path. Containers, module publication and remote installation are not automated
   by this scaffold; do not modify shared drivers or system libraries.
3. Separate versioned software from read-only inputs, a fresh writable run directory
   and results/logs. Use shared absolute paths visible from compute nodes; declare
   scratch staging/copy-back if required. Do not rely on the login shell's cwd or
   unrecorded PATH/library changes.
4. Stage declared files before submission. app.json/run/check are included by the
   planner; put additional code, inputs and archives in files. Directories and
   recursive dependency discovery are not supported: explicitly archive them and
   implement safe extraction/setup in the application. Do not assume compute-node
   Internet access or install unpinned dependencies during every job.
5. Put outputs under results/, retain scheduler/application logs and report missing
   artifacts as failure. Download explicit artifacts, then run the local correctness
   checker against a reference/tolerance. Keep secrets and private run data out of
   the public repository and compatibility report.

For Hygon Z100 DCU / DTK, apply the additional [runtime checks](hygon-z100.md).
Use [scnet-hashcat](hashcat-reference.md) for concrete lifecycle and packaging
examples. A successful descriptor/path check is not proof of site policy compliance,
software installation, scientific correctness or performance.
