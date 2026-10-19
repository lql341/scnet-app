#!/usr/bin/env bash
# Compatibility entry point. The actual build uses a job-unique clean
# OpenFOAM/ThirdParty snapshot; it never mutates the shared source tree.
#SBATCH --job-name=foam2606_gcc16_iso
#SBATCH --partition=<QUEUE>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=03:00:00
set -euo pipefail
base=<OPENFOAM_VALIDATION_ROOT>
exec bash "$base/work/isolated-20261019b/openfoam_build_gcc16_isolated_compute.sbatch"
