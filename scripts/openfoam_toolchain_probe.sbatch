#!/usr/bin/env bash
#SBATCH --job-name=foam2606_toolchain
#SBATCH --partition=<QUEUE>
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:10:00
#SBATCH --output=<OPENFOAM_VALIDATION_ROOT>/toolchain-%j.out
#SBATCH --error=<OPENFOAM_VALIDATION_ROOT>/toolchain-%j.err
set -euo pipefail
bash <OPENFOAM_VALIDATION_ROOT>/openfoam_toolchain_probe.sh \
  <OPENFOAM_VALIDATION_ROOT> \
  <OPENFOAM_VALIDATION_ROOT>/probe
