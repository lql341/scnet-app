#!/usr/bin/env bash
# Remote-only OpenFOAM v2606 GCC 11 isolated build and smoke validation.
# The source and ThirdParty trees are copied on the compute node into a
# job-unique directory, so no two jobs mutate shared lnInclude/platforms data.
#SBATCH --job-name=foam2606_gcc11_iso
#SBATCH --partition=<QUEUE>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=03:00:00
#SBATCH --output=<OPENFOAM_VALIDATION_ROOT>/gcc11-iso-%j.out
#SBATCH --error=<OPENFOAM_VALIDATION_ROOT>/gcc11-iso-%j.err
set -o pipefail

base=<OPENFOAM_VALIDATION_ROOT>
src="$base/openfoam"
third_src="$base/ThirdParty-v2606"
src_commit=481094fdf34f11ed6d0d603ee59a858a0124236d
run="$base/work/runs/gcc11-${SLURM_JOB_ID}"
foam="$run/openfoam"
third="$run/ThirdParty-v2606"
buildroot="$run/buildroot"
log="$run/allwmake.log"
testlog="$run/foamInstallationTest.txt"

module purge
module load openmpi/5.0.11
gcc11=/public/software/compiler/gcc/11.2.0
export PATH="$gcc11/bin:$PATH"
export LD_LIBRARY_PATH="$gcc11/lib64:${LD_LIBRARY_PATH:-}"
export CC="$gcc11/bin/gcc" CXX="$gcc11/bin/g++" FC="$gcc11/bin/gfortran"
export OMPI_CC="$CC" OMPI_CXX="$CXX" OMPI_FC="$FC"

mkdir -p "$run"
mkdir -p "$foam" "$third"
(cd "$src" && git archive --format=tar "$src_commit") | tar -C "$foam" -xf -
tar -C "$third_src" -cf - sources/scotch etc | tar -C "$third" -xf -
test -f "$foam/Allwmake"
test -d "$third/sources/scotch"
cd "$foam"
source etc/bashrc
export PATH="$PWD/wmake:$PATH"
export WM_MPLIB=SYSTEMOPENMPI
export WM_THIRD_PARTY_DIR="$third"
export FOAM_THIRD_PARTY_BUILDROOT="$buildroot"
export FOAM_EXTRA_CXXFLAGS="-D_PSTL_PAR_BACKEND_SERIAL"
mkdir -p "$buildroot"

printf 'host=%s\n' "$(hostname)"
printf 'job_id=%s\n' "$SLURM_JOB_ID"
printf 'gcc=%s\n' "$(gcc --version | head -1)"
printf 'mpicc=%s\n' "$(mpicc --showme:command 2>/dev/null)"
printf 'run=%s\n' "$run"
printf 'FOAM_EXTRA_CXXFLAGS=%s\n' "$FOAM_EXTRA_CXXFLAGS"

set +e
./Allwmake -j "${SLURM_CPUS_PER_TASK:-8}" -s -q -l >"$log" 2>&1
allwmake_rc=$?
foamInstallationTest >"$testlog" 2>&1
install_rc=$?
set -e
printf 'allwmake_rc=%s\n' "$allwmake_rc"
printf 'installation_test_rc=%s\n' "$install_rc"
if [ -x "$FOAM_APPBIN/icoFoam" ]; then printf 'icoFoam=present\n'; else printf 'icoFoam=missing\n'; fi
if grep -Eiq "(error:|fatal error|CMake Error|command not found|No such file)" "$log" "$testlog" 2>/dev/null; then
    printf 'error_markers=present\n'
    exit 2
fi
if [ "$allwmake_rc" -ne 0 ] || [ "$install_rc" -ne 0 ] || [ ! -x "$FOAM_APPBIN/icoFoam" ]; then
    exit 3
fi
exit 0
