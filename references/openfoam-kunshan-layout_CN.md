# 昆山 OpenFOAM v2606 工作目录

远端根目录：

```text
<OPENFOAM_VALIDATION_ROOT>
```

本文件对应远端根目录的 `README.md`。远端结果不应直接复制回本机作为
OpenFOAM 构建证据；本机只保存脚本和验证说明。

## 目录约定

| 路径 | 用途 | 后续处理 |
|---|---|---|
| `openfoam/` | 共享 OpenFOAM v2606 源码输入，含 Git 元数据 | 只读，不在这里编译 |
| `ThirdParty-v2606/` | 共享 ThirdParty 输入 | 只读，不在这里编译 |
| `work/runs/gcc11-<JOB_ID>/` | GCC11 最终独立构建和 cavity 结果 | 保留，作为 GCC11 核心证据 |
| `work/runs/gcc16-<JOB_ID>/` | GCC16 最终独立构建、cavity 结果 | 保留，作为 GCC16 核心证据 |
| `work/runs/gcc16-post-<JOB_ID>/` | GCC16 clean-install、幂等性、relocation 日志 | 保留，作为 post-build 证据 |
| `work/runs/gcc16-post-<JOB_ID>/` | 已取消的慢速复制尝试 | 保留历史记录，不作为成功证据 |
| `work/runs/gcc11-<JOB_ID>/`、`gcc11-<JOB_ID>/` | 已取消/失败的早期尝试 | 保留失败证据，不复用 build |
| `work/isolated-20261019b/` | 上传的作业脚本、探针和 Slurm 输出 | 继续作为脚本入口和作业日志目录 |
| `probe/` | 早期工具链探针结果 | 仅作历史参考 |
| `gcc16-isolated*`、`build*.out/err` | 根目录旧作业产物 | 不删除，除非先确认无外部引用 |

## 当前验收状态

- GCC11 独立构建作业：`<JOB_ID>`，平台退出状态 0。
- GCC11 cavity smoke：`<JOB_ID>`，`blockMesh`、`icoFoam` 和重复安装测试通过。
- GCC16 独立构建作业：`<JOB_ID>`，平台退出状态 0，`allwmake_rc=0`，
  `installation_test_rc=0`，`icoFoam=present`。
- GCC16 cavity smoke：`<JOB_ID>`，`blockMesh`、`icoFoam` 和重复安装测试通过。
- GCC16 post-build：`<JOB_ID>`，clean-shell、两次幂等性和 relocation 测试通过。

GCC16 构建使用：

```text
compiler/dtk/26.04
openmpi/5.0.11
WM_CFLAGS += -std=gnu17
FOAM_EXTRA_CXXFLAGS=-D_PSTL_PAR_BACKEND_SERIAL
```

GCC11 构建使用 GCC 11.2.0、OpenMPI 5.0.11 和同一个串行 PSTL 选项。
GCC11/GCC16 不得共享源码树、`buildroot`、`platforms`、`lnInclude` 或可变
ThirdParty 目录。

## 后续工作

完整 `Allwmake` 已经完成一次性工具链验收，不应作为日常回归测试。后续优先
复用已验收安装，只运行：

1. 工具链/MPI/PSTL probe；
2. `foamInstallationTest`；
3. `blockMesh`；
4. 短时 `icoFoam` cavity；
5. 必要的数值日志检查。

源码变更需要重新验证时，创建新的 `work/runs/<toolchain>-<job-id>/`，不要
覆盖现有结果。提交和等待优先使用：

```bash
python3 <SCNET_HPC>/scripts/scnet.py \
  --backend openapi --cluster kseshell --json jobs --scope active --limit 20
```

查询单个作业：

```bash
python3 <SCNET_HPC>/scripts/scnet.py \
  --backend openapi --cluster kseshell --json job JOB_ID
```

远端结果保留策略：不删除、不覆盖已有作业目录；新的日志和验证结果使用新的
作业号和新的 `work/runs` 子目录。
