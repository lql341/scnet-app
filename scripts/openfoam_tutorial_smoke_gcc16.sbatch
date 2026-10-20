#!/usr/bin/env bash
# Run a short blockMesh + icoFoam cavity tutorial against one accepted
# GCC16 installation. All writes stay below the job's unique run directory.
#SBATCH --job-name=foam2606_gcc16_smoke
#SBATCH --partition=<QUEUE>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:30:00
set -o pipefail

base=<OPENFOAM_VALIDATION_ROOT>
run="${FOAM_VALIDATION_RUN:-$base/work/runs/gcc16-<JOB_ID>}"
foam="$run/openfoam"
case_root="$run/validation/cavity-${SLURM_JOB_ID}"
source_case="$foam/tutorials/incompressible/icoFoam/cavity/cavity"

module purge
module load compiler/dtk/26.04 openmpi/5.0.11
export PATH="$foam/wmake:$PATH"
export WM_MPLIB=SYSTEMOPENMPI
export FOAM_EXTRA_CXXFLAGS="-D_PSTL_PAR_BACKEND_SERIAL"

cd "$foam"
source etc/bashrc
export PATH="$foam/wmake:$PATH"
mkdir -p "$case_root"
cp -a "$source_case"/. "$case_root"
sed -i 's/^endTime[[:space:]]*0.5;/endTime         0.05;/' \
    "$case_root/system/controlDict"
cd "$case_root"

set +e
blockMesh > blockMesh.log 2>&1
blockmesh_rc=$?
icoFoam > icoFoam.log 2>&1
icofoam_rc=$?
foamInstallationTest > installation-repeat.log 2>&1
repeat_rc=$?
set -e

printf 'blockMesh_rc=%s\n' "$blockmesh_rc"
printf 'icoFoam_rc=%s\n' "$icofoam_rc"
printf 'installation_repeat_rc=%s\n' "$repeat_rc"
test "$blockmesh_rc" -eq 0
test "$icofoam_rc" -eq 0
test "$repeat_rc" -eq 0
grep -q "End" icoFoam.log
exit 0
