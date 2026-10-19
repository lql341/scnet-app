#!/bin/bash -l
# Probe OpenFOAM v2606's compiler/MPI/PSTL prerequisites on a remote SCNet node.
set -u

WORK_ROOT="${1:-<OPENFOAM_VALIDATION_ROOT>}"
OUT_DIR="${2:-${WORK_ROOT}/probe}"
mkdir -p "${OUT_DIR}"
LOG="${OUT_DIR}/toolchain-probe-${SLURM_JOB_ID:-interactive}.log"
exec > >(tee "${LOG}") 2>&1

rc=0
fail() {
    echo "FAIL: $*"
    rc=1
}

echo "host=$(hostname)"
echo "date=$(date -Is)"
echo "job_id=${SLURM_JOB_ID:-none}"
echo "partition=${SLURM_JOB_PARTITION:-none}"

module purge
module load compiler/gcc/11.2.0 || fail "compiler/gcc/11.2.0"
module load openmpi/5.0.11 || fail "openmpi/5.0.11"

GCC11_PREFIX="/public/software/compiler/gcc/11.2.0"
export PATH="${GCC11_PREFIX}/bin:<OPENMPI_PREFIX>/bin:${PATH}"
export CC="${GCC11_PREFIX}/bin/gcc"
export CXX="${GCC11_PREFIX}/bin/g++"
export FC="${GCC11_PREFIX}/bin/gfortran"
export OMPI_CC="${CC}"
export OMPI_CXX="${CXX}"
export OMPI_FC="${FC}"

echo "gcc=$(command -v gcc || true)"
gcc --version | head -1 || fail "gcc version"
echo "gxx=$(command -v g++ || true)"
g++ --version | head -1 || fail "g++ version"
echo "mpicc=$(command -v mpicc || true)"
mpicc --showme:command 2>&1 || true
mpicc --showme:compile 2>&1 || true
echo "mpicxx=$(command -v mpicxx || true)"
mpicxx --showme:command 2>&1 || true
mpicxx --showme:compile 2>&1 || true
echo "OMPI_CC=${OMPI_CC}"
echo "OMPI_CXX=${OMPI_CXX}"

PROBE_DIR="${OUT_DIR}/compile-${SLURM_JOB_ID:-interactive}"
rm -rf "${PROBE_DIR}"
mkdir -p "${PROBE_DIR}"

cat > "${PROBE_DIR}/mpi_probe.c" <<'EOF'
#include <mpi.h>
int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);
    MPI_Finalize();
    return 0;
}
EOF

cat > "${PROBE_DIR}/pstl_probe.cpp" <<'EOF'
#include <algorithm>
#include <execution>
#include <numeric>
#include <vector>
int main() {
    std::vector<int> v(1024, 1);
    std::sort(std::execution::par, v.begin(), v.end());
    return std::accumulate(v.begin(), v.end(), 0) == 1024 ? 0 : 1;
}
EOF

cat > "${PROBE_DIR}/mpi_cpp_probe.cpp" <<'EOF'
#include <mpi.h>
#include <execution>
#include <vector>
#include <algorithm>
int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);
    std::vector<int> v(32, 1);
    std::sort(std::execution::par, v.begin(), v.end());
    MPI_Finalize();
    return v[0] == 1 ? 0 : 1;
}
EOF

echo "== mpi C =="
mpicc "${PROBE_DIR}/mpi_probe.c" -o "${PROBE_DIR}/mpi_probe" || fail "mpi C compile"
echo "== pstl C++ =="
g++ -std=c++17 -D_PSTL_PAR_BACKEND_SERIAL "${PROBE_DIR}/pstl_probe.cpp" -o "${PROBE_DIR}/pstl_probe" || fail "PSTL serial C++ compile"
echo "== mpi C++ + PSTL =="
mpicxx -std=c++17 -D_PSTL_PAR_BACKEND_SERIAL "${PROBE_DIR}/mpi_cpp_probe.cpp" -o "${PROBE_DIR}/mpi_cpp_probe" || fail "MPI C++/PSTL serial compile"

if [[ -x "${PROBE_DIR}/mpi_probe" ]]; then
    "${PROBE_DIR}/mpi_probe" || fail "mpi C run"
fi
if [[ -x "${PROBE_DIR}/pstl_probe" ]]; then
    "${PROBE_DIR}/pstl_probe" || fail "PSTL run"
fi
if [[ -x "${PROBE_DIR}/mpi_cpp_probe" ]]; then
    "${PROBE_DIR}/mpi_cpp_probe" || fail "MPI C++/PSTL run"
fi

echo "probe_rc=${rc}"
exit "${rc}"
