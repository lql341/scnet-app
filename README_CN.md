# scnet-app

[English](README.md) | 中文

版本：0.1.0

将 HPC、AI4S 和科学智能计算应用适配为 [SCNet](https://www.scnet.cn) 应用 skill 的
轻量元 skill，优先面向 **海光 Z100 DCU / DTK**。
它生成统一仓库和可审阅的 SCNet 作业计划，基础设施由
[scnet-hpc](https://github.com/lql341/scnet-hpc) 提供，应用保留自己的科学逻辑及正确性检查。

设计吸收了 [scnet-hashcat](https://github.com/lql341/scnet-hashcat) 的实践经验。
已有分布式驱动不宣称由本工具生成，也未迁入本版单节点规范。

## 一句话安装

> 使用 `$skill-installer` 从 GitHub 仓库 `lql341/scnet-app` 根目录（path `.`、ref `main`）安装 `scnet-app`，保留已有目录；在安装目录用 Python 3 运行 `scripts/scnet_app.py --help` 并报告绝对路径；安装时不配置凭证、不申请算力。

其他支持 SKILL.md 的宿主按其规范安装整个根目录并刷新发现列表。
Codex 默认目录为 `$CODEX_HOME/skills/scnet-app` 或 `~/.codex/skills/scnet-app`，下一轮调用。
克隆后可用 CLI，但不会自动向 agent 注册 skill：

```bash
git clone https://github.com/lql341/scnet-app.git
cd scnet-app
python3 scripts/scnet_app.py --help
```

本地只需 Python 3.8+ 标准库。Windows 使用 `python` 或 `py -3`。
生成脚手架不需要本地 GPU、DTK、PyTorch、账户秘密或 pip 包。
可选 PyTorch 探针有独立的远端框架前置条件。

## 一句话让 agent 适配应用

> 使用 `$scnet-app` 把我提供的科学计算应用整理成 SCNet 应用 skill，优先适配海光 Z100；检查许可证和依赖，选择最小可用实现，补齐中英文安装使用说明，定义真实正确性检查，并准备 1 节点 1 DCU 的 SCNet 小测试计划；获得计算节点证据前保持未验证状态，没有授权预算时不提交作业。

提供上游仓库/版本、代表性输入/参考值、已知环境限制；需要实测时说明算力预算。
已有应用仓库可原地采用同一规范；init 只创建新目录，不覆盖已有工作。

## 最简流程

将 OWNER/PROJECT 换成实际上游，将引号中的目录换成真实路径。
以下命令在安装后的 scnet-app 根目录执行：

```bash
python3 scripts/scnet_app.py init scnet-myapp --output ../scnet-myapp --upstream https://github.com/OWNER/PROJECT
python3 scripts/scnet_app.py validate ../scnet-myapp
python3 scripts/scnet_app.py plan ../scnet-myapp --scnet-hpc "/absolute/scnet-hpc" --remote-dir "/absolute/remote/fresh-run"
```

产物是脚手架，尚未完成应用移植。编辑 app.json，实现运行/检查钩子及科学验收条件。
原始钩子会失败退出；保留原始钩子或验收条件时，plan 的 `submit` 为 null。
打包校验或计划生成成功始终仍显示 `compute_verified: false`。

随后阅读[应用规范](references/contract_CN.md)，做只读预检：

```bash
python3 scripts/scnet_app.py doctor ../scnet-myapp --scnet-hpc "/absolute/scnet-hpc"
```

检查实时账户、队列、配额以及生成的 scnet-hpc `--dry-run` 预览。
实现和授权预算就绪后，由 scnet-hpc 执行计划中的传输/提交、有限等待、状态查询、
明确产物下载和取消。本元 skill CLI 不执行远端修改。
plan 不预留远端目录，每次运行须选一个新的独立目录。

## 分阶段前置条件

| 阶段 | 前置条件 |
| --- | --- |
| init / validate | 本地 Python 3.8+ 和完整仓库 |
| plan | 另需本地 scnet-hpc >=0.6.13，适配接口按 0.6.13 验证；不需凭证/联网 |
| doctor | 另需 SCNet 网络、已开通区域/队列、scnet-hpc 凭证 |
| 真实应用作业 | 余额/配额、已准备输入/依赖、共享可写存储、兼容应用/DTK 环境和所申请设备 |

用 `--scnet-hpc`、`SCNET_HPC_ROOT` 指定基础 skill 目录，或使用标准 Codex 安装位置。
凭证只走 scnet-hpc 的 setup、环境变量或系统存储。app.json 不保存 AK/SK、token、
SSH 私钥或接口地址。本地安装不部署科学应用，也不开通 SCNet 资源。

## 范围和 Z100 适配

默认示例为昆山 `kseshell` / 区域 `<REGION_ID>` / `<QUEUE>`，1 节点、共 8 核、1 DCU、
3 分钟，不代表实时可用性。`--target hygon-c86` 显式生成 CPU 应用，默认零 DCU 和
CPU 队列。实时调度/profile 事实优先于硬件提示。

v0.1 先规范**单节点**验证。尚未实现 MPI、多节点 fan-out、数组作业、CUDA 自动转换
或远端软件部署；本脚手架不宣称任何应用已适配成功。
ABI/工具链、算子/精度、显存和数值验证边界见[Z100 指南](references/hygon-z100_CN.md)。

目录采用 SKILL.md、agents、schema、scripts、assets、targets、references、tests 分层。
共享基础能力调用 scnet-hpc，不再复制认证、文件或作业客户端。

```bash
python3 -m unittest discover -s tests -v
python3 scripts/validate_repo.py
```

首轮验证：Windows Python 3.12 上的 12 项行为/协议测试通过，包含真实 scnet-hpc
无凭证离线提交预览；昆山只读 doctor/resource-summary 接入成功。
本脚手架未申请计算资源或完成实际应用适配。CI 覆盖 Ubuntu Python 3.8/3.12 和
Windows Python 3.12，具体结果以当前提交检查为准。

MIT 仅覆盖脚手架，上游应用、模型和数据遵循各自许可证。
