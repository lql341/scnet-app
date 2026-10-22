#!/usr/bin/env bash
#SBATCH --job-name=foam2606_toolchain
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:10:00
#SBATCH --output=toolchain-%j.out
#SBATCH --error=toolchain-%j.err
set -euo pipefail
base="${OPENFOAM_VALIDATION_ROOT:?set OPENFOAM_VALIDATION_ROOT}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$script_dir/openfoam_toolchain_probe.sh" "$base" "$base/probe"
