#!/usr/bin/env bash
# Validate a completed GCC16 OpenFOAM tree from a clean shell and a relocated
# read-only hard-link tree. The tree is job-unique and never replaces a result.
#SBATCH --job-name=foam2606_gcc16_post
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:30:00
set -o pipefail

base="${OPENFOAM_VALIDATION_ROOT:?set OPENFOAM_VALIDATION_ROOT}"
run="${FOAM_VALIDATION_RUN:?set FOAM_VALIDATION_RUN to an accepted run directory}"
foam="$run/openfoam"
post="$base/work/runs/gcc16-post-${SLURM_JOB_ID}"
reloc="$post/openfoam-relocated"

module purge
module load compiler/dtk/26.04 openmpi/5.0.11
export FOAM_EXTRA_CXXFLAGS="-D_PSTL_PAR_BACKEND_SERIAL"

set +e
mkdir -p "$post"
bash -c "cd '$foam' && source etc/bashrc && foamInstallationTest" \
    >"$post-clean-install.log" 2>&1
clean_install_rc=$?

bash -c "cd '$foam' && source etc/bashrc && foamInstallationTest" \
    >"$post-idempotent-1.log" 2>&1
idempotent_first_rc=$?
bash -c "cd '$foam' && source etc/bashrc && foamInstallationTest" \
    >"$post-idempotent-2.log" 2>&1
idempotent_second_rc=$?

# Hard links avoid another multi-gigabyte copy. No build command is run against
# the relocated tree, so the original build artifacts remain unchanged.
cp -al "$foam" "$reloc"
bash -c "cd '$reloc' && source etc/bashrc && foamInstallationTest" \
    >"$post-relocation.log" 2>&1
relocation_rc=$?
set -e

printf 'clean_install_rc=%s\n' "$clean_install_rc"
printf 'idempotent_first_rc=%s\n' "$idempotent_first_rc"
printf 'idempotent_second_rc=%s\n' "$idempotent_second_rc"
printf 'relocation_rc=%s\n' "$relocation_rc"

test "$clean_install_rc" -eq 0
test "$idempotent_first_rc" -eq 0
test "$idempotent_second_rc" -eq 0
test "$relocation_rc" -eq 0
grep -q "Done" "$post-clean-install.log"
grep -q "Done" "$post-idempotent-1.log"
grep -q "Done" "$post-idempotent-2.log"
grep -q "Done" "$post-relocation.log"
exit 0
