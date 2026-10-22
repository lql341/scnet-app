#!/usr/bin/env bash
# Compatibility entry point. The actual build uses a job-unique clean
# OpenFOAM/ThirdParty snapshot; it never mutates the shared source tree.
#SBATCH --job-name=foam2606_gcc11_iso
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=03:00:00
set -euo pipefail
base="${OPENFOAM_VALIDATION_ROOT:?set OPENFOAM_VALIDATION_ROOT}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$script_dir/openfoam_build_gcc11_isolated.sbatch"
