#!/usr/bin/env bash
# Remote-only retry: force libstdc++ PSTL serial backend because the cluster TBB
# headers do not provide tbb::this_task_arena.
#SBATCH --job-name=foam2606_gcc11_serial
#SBATCH --partition=<QUEUE>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
#SBATCH --output=<OPENFOAM_VALIDATION_ROOT>/serial-%j.out
#SBATCH --error=<OPENFOAM_VALIDATION_ROOT>/serial-%j.err
set -o pipefail

base=<OPENFOAM_VALIDATION_ROOT>
foam="$base/openfoam"

module purge
module load openmpi/5.0.11

gcc11=/public/software/compiler/gcc/11.2.0
export PATH="$gcc11/bin:$PATH"
export LD_LIBRARY_PATH="$gcc11/lib64:${LD_LIBRARY_PATH:-}"
export CC="$gcc11/bin/gcc" CXX="$gcc11/bin/g++" FC="$gcc11/bin/gfortran"
export OMPI_CC="$CC" OMPI_CXX="$CXX" OMPI_FC="$FC"

cd "$foam"
source etc/bashrc
export PATH="$PWD/wmake:$PATH"
export WM_MPLIB=SYSTEMOPENMPI
export FOAM_EXTRA_CXXFLAGS=-D_PSTL_PAR_BACKEND_SERIAL

rm -rf "$foam/build/linux64GccDPInt32Opt" \
       "$foam/platforms/linux64GccDPInt32Opt" \
       "$foam/applications/bin/linux64GccDPInt32Opt" \
       "$foam/lib/linux64GccDPInt32Opt"
rm -f "$foam/log.linux64GccDPInt32Opt"

printf 'host=%s\n' "$(hostname)"
printf 'gcc=%s\n' "$(gcc --version | head -1)"
printf 'pstl_backend=%s\n' "$FOAM_EXTRA_CXXFLAGS"

set +e
./Allwmake -j 8 -s -q -l
allwmake_rc=$?
set -e
printf 'allwmake_rc=%s\n' "$allwmake_rc"

set +e
foamInstallationTest > "$base/foamInstallationTest-gcc11-serial-${SLURM_JOB_ID}.txt" 2>&1
install_rc=$?
set -e
printf 'installation_test_rc=%s\n' "$install_rc"

if [ -x "$FOAM_APPBIN/icoFoam" ]; then
  printf 'icoFoam=present\n'
else
  printf 'icoFoam=missing\n'
fi

if grep -Eiq "(error:|fatal error|\*\*\* not installed|CRITICAL ERROR|command not found|No such file)" \
    "$foam/log.linux64GccDPInt32Opt" \
    "$base/foamInstallationTest-gcc11-serial-${SLURM_JOB_ID}.txt" 2>/dev/null; then
  printf 'error_markers=present\n'
  exit 2
fi

if [ "$allwmake_rc" -ne 0 ] || [ "$install_rc" -ne 0 ] || [ ! -x "$FOAM_APPBIN/icoFoam" ]; then
  exit 3
fi
exit 0
