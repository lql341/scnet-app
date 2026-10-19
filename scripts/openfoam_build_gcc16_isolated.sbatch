#!/usr/bin/env bash
# Remote-only OpenFOAM v2606 GCC 16 validation.
#
# The buildroot keeps generated ThirdParty artifacts separate from the source
# tree. Scotch 6.1.0 uses old C function-pointer declarations which GCC 16
# rejects unless compiled with a GNU C dialect where () retains legacy
# compatibility. FOAM_EXTRA_CXXFLAGS selects the serial libstdc++ PSTL path
# and avoids the cluster's incompatible legacy TBB headers.
#SBATCH --job-name=foam2606_gcc16_iso
#SBATCH --partition=<QUEUE>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=03:00:00
#SBATCH --output=<OPENFOAM_VALIDATION_ROOT>/gcc16-iso-%j.out
#SBATCH --error=<OPENFOAM_VALIDATION_ROOT>/gcc16-iso-%j.err

set -o pipefail

base=<OPENFOAM_VALIDATION_ROOT>
foam="$base/openfoam"
third="$base/ThirdParty-v2606"
buildroot="$base/gcc16-isolated"
log="$base/gcc16-isolated-${SLURM_JOB_ID}.log"
testlog="$base/foamInstallationTest-gcc16-isolated-${SLURM_JOB_ID}.txt"

module purge
module load compiler/dtk/26.04 openmpi/5.0.11

cd "$foam"
source etc/bashrc
export PATH="$PWD/wmake:$PATH"
export WM_MPLIB=SYSTEMOPENMPI
export WM_THIRD_PARTY_DIR="$third"

# Keep all generated ThirdParty build/install output isolated.
export FOAM_THIRD_PARTY_BUILDROOT="$buildroot"

# Scotch 6.1.0 is C code using legacy () function-pointer declarations.
# Keep this C-only; OpenFOAM C++ remains C++17.
export WM_CFLAGS="$(wmake -show-cflags) -std=gnu17"

# GCC 16's libstdc++ sees the cluster TBB 2018 headers but cannot use the
# expected tbb::this_task_arena API. OpenFOAM's wmake rules honor this flag.
export FOAM_EXTRA_CXXFLAGS="-D_PSTL_PAR_BACKEND_SERIAL"

printf 'host=%s\n' "$(hostname)"
printf 'job_id=%s\n' "${SLURM_JOB_ID:-none}"
printf 'gcc=%s\n' "$(gcc --version | head -1)"
printf 'gxx=%s\n' "$(g++ --version | head -1)"
printf 'mpicc=%s\n' "$(mpicc --showme:command 2>/dev/null || command -v mpicc)"
printf 'WM_PROJECT_VERSION=%s\n' "$WM_PROJECT_VERSION"
printf 'WM_MPLIB=%s\n' "$WM_MPLIB"
printf 'WM_CFLAGS=%s\n' "$WM_CFLAGS"
printf 'FOAM_EXTRA_CXXFLAGS=%s\n' "$FOAM_EXTRA_CXXFLAGS"
printf 'FOAM_THIRD_PARTY_BUILDROOT=%s\n' "$FOAM_THIRD_PARTY_BUILDROOT"

rm -f "$log" "$testlog"
set +e
./Allwmake -j "${SLURM_CPUS_PER_TASK:-8}" -s -q -l >"$log" 2>&1
allwmake_rc=$?
set -e
printf 'allwmake_rc=%s\n' "$allwmake_rc"

set +e
foamInstallationTest >"$testlog" 2>&1
install_rc=$?
set -e
printf 'installation_test_rc=%s\n' "$install_rc"

if [ -x "$FOAM_APPBIN/icoFoam" ]; then
    printf 'icoFoam=present\n'
else
    printf 'icoFoam=missing\n'
fi

# Allwmake may return zero after optional component failures. Treat missing
# solver/core artifacts and hard compiler errors as failure evidence.
if grep -Eiq "(error:|fatal error|CMake Error|command not found|No such file)" \
    "$log" "$testlog" 2>/dev/null; then
    printf 'error_markers=present\n'
    exit 2
fi

if [ "$allwmake_rc" -ne 0 ] || [ "$install_rc" -ne 0 ] || \
   [ ! -x "$FOAM_APPBIN/icoFoam" ]; then
    exit 3
fi
exit 0
