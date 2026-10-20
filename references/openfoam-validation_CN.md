# OpenFOAM v2606 远端构建验收

本流程只在昆山 `kseshell` 计算节点执行 OpenFOAM 编译、安装测试、tutorial
和数值验证。本机不编译 OpenFOAM。调度优先使用 scnet-hpc OpenAPI；SSH 只用于
上传脚本、读取日志和必要诊断。

昆山远端目录、保留结果和后续入口见
[昆山 OpenFOAM 工作目录](openfoam-kunshan-layout_CN.md)。远端根目录同时保留
同内容的 `README.md`。

## 独立目录

共享源码只作为只读输入：

```text
<OPENFOAM_VALIDATION_ROOT>/openfoam
<OPENFOAM_VALIDATION_ROOT>/ThirdParty-v2606
```

每个作业在唯一的 `work/runs/<toolchain>-<job-id>/` 中创建源码、ThirdParty、
buildroot、platforms、lnInclude 和日志。OpenFOAM 源码由固定提交
`481094fdf34f11ed6d0d603ee59a858a0124236d` 通过 `git archive` 生成；ThirdParty
只复制 Scotch 源码 `sources/scotch` 和 `etc`，不复制已有 `build`、`platforms`
或生成的 lnInclude。
GCC11 与 GCC16 不并发写入任何目录。

## 工具链约束

- GCC11：`/public/software/compiler/gcc/11.2.0`，OpenMPI `5.0.11`，通过
  `OMPI_CC/OMPI_CXX/OMPI_FC` 指定底层编译器。
- GCC16：`compiler/dtk/26.04` 与 OpenMPI `5.0.11`，Scotch C 编译增加
  `-std=gnu17`。
- 昆山旧 TBB 与 GCC11/GCC16 的 libstdc++ PSTL backend 不兼容。构建和探针都必须
  使用 `-D_PSTL_PAR_BACKEND_SERIAL`。
- 系统 GCC 4.8.5、旧 CMake 和可选 KAHIP/ADIOS2 失败不能单独判定 OpenFOAM 核心失败。

## 成功门槛

不得把 `Allwmake` 返回 0 单独当作成功。作业必须同时保留并检查：

1. `allwmake_rc=0`；
2. `foamInstallationTest` 的真实输出和 `installation_test_rc=0`；
3. `FOAM_APPBIN/icoFoam` 存在且可执行；
4. `Allwmake`、安装测试和作业输出中没有真实 `error:`、`fatal error`、
   `CMake Error`、`command not found` 或 `No such file` 标记；
5. OpenAPI 作业为 `COMPLETED`，平台退出状态为 0，且日志中的工作目录、队列、
   CPU 与提交请求一致。

核心构建通过后，继续在同一独立安装中运行 `blockMesh`、`icoFoam`、短 tutorial、
clean-install、relocation 和 idempotency；每项都保存原始日志和退出码。

## 已确认证据

- 作业 `<JOB_ID>`：GCC11/OpenMPI 默认 PSTL 失败，出现旧 TBB
  `tbb::this_task_arena` 错误；该作业作为失败证据。
- 作业 `<JOB_ID>`：GCC11.2/OpenMPI 5.0.11 的 MPI C、串行 PSTL C++、
  MPI+PSTL 探针全部通过，平台退出状态为 0。
- 作业 `<JOB_ID>`：旧 `cp -a` 复制共享源码时遇到
  `build/linux64GccDPInt32Opt/_project_.Makefile` 缺失，已取消，不能作为构建证据。
- 作业 `<JOB_ID>`：使用 Git/ThirdParty 快照的 GCC11 作业因 ThirdParty 全量复制
  过慢而取消，未产生构建证据。
- 作业 `<JOB_ID>`：GCC11 独立构建完成，`allwmake_rc=0`、
  `installation_test_rc=0`、`icoFoam=present`，OpenAPI 平台退出状态为 0。
- 作业 `<JOB_ID>`：同一 GCC11 安装的 cavity tutorial smoke 完成，
  `blockMesh_rc=0`、`icoFoam_rc=0`、重复安装测试为 0，日志到达 `End`。
- 作业 `<JOB_ID>`：GCC16.2/OpenMPI 5.0.11 独立源码树完成，使用
  `-std=gnu17` 修复 Scotch C 兼容性，并使用串行 PSTL backend；平台退出状态为
  0，`allwmake_rc=0`、`installation_test_rc=0`、`icoFoam=present`。安装测试输出
  `Base configuration ok.`、`Critical systems ok.`、`Done`，未发现真实错误标记。
- 作业 `<JOB_ID>`：同一 GCC16 安装的 cavity tutorial smoke 完成，平台退出状态
  为 0；`blockMesh_rc=0`、`icoFoam_rc=0`、重复安装测试为 0，日志到达 `End`，
  最终时间为 `0.05`，连续性误差约 `1e-9`。
- 作业 `<JOB_ID>`：GCC16 clean-shell 安装测试、两次幂等性检查和 job-unique
  relocation 硬链接树测试均通过，平台退出状态为 0；四份日志均包含 `Done`，
  relocation 日志确认 `icoFoam` 可执行文件仍可见。

## 验证分层

完整 `Allwmake` 会编译全部 OpenFOAM 库和应用，包含多相、颗粒、分子、伴随和
网格工具，适合每个工具链/源码提交做一次发行验收，不适合作为日常回归 case。
日常验证复用已验收的独立安装，只运行工具链探针、`foamInstallationTest`、
`blockMesh`、短时 `icoFoam` cavity 和数值日志检查。源码改动需要重新验证时，
优先增加定向库/应用构建，不要默认重复全量 `Allwmake`。

## 调度命令

```bash
python3 <SCNET_HPC>/scripts/scnet.py \
  --backend openapi --cluster kseshell wait JOB_ID \
  --wait-timeout 300 --interval 20
```

等待超时只表示轮询结束，不表示作业失败；先查询 `job JOB_ID`，再读取作业输出、
构建日志和安装测试。取消必须明确指定作业号，不能取消或覆盖用户已有远端结果。
