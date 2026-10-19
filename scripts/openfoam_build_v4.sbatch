#!/usr/bin/env bash
#SBATCH --job-name=foam2606_gcc11
#SBATCH --partition=<QUEUE>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
#SBATCH --output=<OPENFOAM_VALIDATION_ROOT>/build4-%j.out
#SBATCH --error=<OPENFOAM_VALIDATION_ROOT>/build4-%j.err
set -o pipefail

base=<OPENFOAM_VALIDATION_ROOT>
foam="$base/openfoam"
third="$base/ThirdParty-v2606"

module purge
module load openmpi/5.0.11

# OpenMPI 5.0.11 loads GCC 16.2 internally.  Keep that MPI installation,
# but explicitly select the independently installed GCC 11 toolchain for
# OpenFOAM and its ThirdParty C/C++ builds.
gcc11=/public/software/compiler/gcc/11.2.0
export PATH="$gcc11/bin:$PATH"
export LD_LIBRARY_PATH="$gcc11/lib64:${LD_LIBRARY_PATH:-}"
export CC="$gcc11/bin/gcc"
export CXX="$gcc11/bin/g++"
export FC="$gcc11/bin/gfortran"
export OMPI_CC="$CC"
export OMPI_CXX="$CXX"
export OMPI_FC="$FC"

cd "$foam"
source etc/bashrc
export PATH="$PWD/wmake:$PATH"
export WM_MPLIB=SYSTEMOPENMPI

printf 'host=%s\n' "$(hostname)"
printf 'gcc=%s\n' "$(gcc --version | head -1)"
printf 'gxx=%s\n' "$(g++ --version | head -1)"
printf 'mpicc=%s\n' "$(mpicc --showme:command)"
printf 'mpicxx=%s\n' "$(mpicxx --showme:command)"
printf 'WM_PROJECT_VERSION=%s\n' "$WM_PROJECT_VERSION"
printf 'WM_MPLIB=%s\n' "$WM_MPLIB"
printf 'WM_THIRD_PARTY_DIR=%s\n' "${WM_THIRD_PARTY_DIR:-unset}"

# Keep the remote source tree intact; only remove generated build/install
# artifacts from this OpenFOAM configuration.
rm -rf "$foam/build/linux64GccDPInt32Opt" \
       "$foam/platforms/linux64GccDPInt32Opt" \
       "$foam/applications/bin/linux64GccDPInt32Opt" \
       "$foam/lib/linux64GccDPInt32Opt"
rm -f "$foam/log.linux64GccDPInt32Opt"

set +e
./Allwmake -j 8 -s -q -l
allwmake_rc=$?
set -e
printf 'allwmake_rc=%s\n' "$allwmake_rc"

set +e
foamInstallationTest > "$base/foamInstallationTest-gcc11-%j.txt" 2>&1
install_rc=$?
set -e
printf 'installation_test_rc=%s\n' "$install_rc"

if [ -x "$FOAM_APPBIN/icoFoam" ]; then
  printf 'icoFoam=present\n'
else
  printf 'icoFoam=missing\n'
fi

if grep -Eiq "(error:|fatal error|\*\*\* not installed|CRITICAL ERROR|command not found|No such file)" \
    "$foam/log.linux64GccDPInt32Opt" "$base/foamInstallationTest-gcc11-%j.txt" 2>/dev/null; then
  printf 'error_markers=present\n'
  exit 2
fi

if [ "$allwmake_rc" -ne 0 ] || [ "$install_rc" -ne 0 ] || [ ! -x "$FOAM_APPBIN/icoFoam" ]; then
  exit 3
fi
exit 0
