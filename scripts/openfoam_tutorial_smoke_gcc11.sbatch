#!/usr/bin/env bash
# Run a short blockMesh + icoFoam cavity tutorial against one accepted
# GCC11 installation. All writes stay below the job's unique run directory.
#SBATCH --job-name=foam2606_gcc11_smoke
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:30:00
set -o pipefail

base="${OPENFOAM_VALIDATION_ROOT:?set OPENFOAM_VALIDATION_ROOT}"
run="${FOAM_VALIDATION_RUN:?set FOAM_VALIDATION_RUN to an accepted run directory}"
foam="$run/openfoam"
case_root="$run/validation/cavity-${SLURM_JOB_ID}"
source_case="$foam/tutorials/incompressible/icoFoam/cavity/cavity"

module purge
module load openmpi/5.0.11
gcc11=${GCC11_PREFIX:-/public/software/compiler/gcc/11.2.0}
export PATH="$gcc11/bin:$foam/wmake:$PATH"
export LD_LIBRARY_PATH="$gcc11/lib64:${LD_LIBRARY_PATH:-}"
export CC="$gcc11/bin/gcc" CXX="$gcc11/bin/g++" FC="$gcc11/bin/gfortran"
export OMPI_CC="$CC" OMPI_CXX="$CXX" OMPI_FC="$FC"
cd "$foam"
source etc/bashrc
export PATH="$foam/wmake:$PATH"
export WM_MPLIB=SYSTEMOPENMPI
export FOAM_EXTRA_CXXFLAGS="-D_PSTL_PAR_BACKEND_SERIAL"

mkdir -p "$case_root"
cp -a "$source_case"/. "$case_root"
sed -i 's/^endTime[[:space:]]*0.5;/endTime         0.05;/' "$case_root/system/controlDict"
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
test -f "postProcessing" 2>/dev/null || true
exit 0
