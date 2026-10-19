# __APP_NAME__

[English](README.md) | 中文

版本：0.1.0。上游：__UPSTREAM__。目标：`__TARGET__`。
状态：脚手架，尚未声明应用或计算节点适配通过。

按[源码到 skill 的适配循环](references/adaptation-loop_CN.md)完成 delivery.json、
runtime/app/、runtime/case/、runtime/scripts/。每次测试后保存记录并运行 scnet-app `gate`；
全部满足后由 `build` 生成 skill 和官方软件包。交付前把本段替换为实测过的中英文安装、
前置条件、一键算例与使用教程。

## 安装和前置条件

将完整 skill 放进 agent 文档规定的技能目录。应用仓库发布后，应将本段换成该仓库
准确的一句话安装提示语，并在干净目录测试。本工具不会自动发布生成的应用仓库。

本地 Python 3.8+、scnet-hpc >=0.6.13 用于编排。真实运行需已开通相应区域/队列的
SCNet 账户、余额/配额、共享可写存储，以及计算节点上兼容的应用/DTK 环境。
复用 scnet-hpc 凭证，app.json 不存秘密。本地安装不安装上游应用，不开通算力权限。

## 适配和使用

按[集群接入清单](references/cluster-integration_CN.md)落实 SCNet 算力绑定、
Slurm 调度及运行包要求。运行行为参考标杆
[scnet-hashcat](https://github.com/lql341/scnet-hashcat)，科学验收标准由本应用定义。

1. 检查上游许可证、构建系统、依赖及代表性输入。
2. 编辑 app.json：区域/队列、完整六轴 stack、prerequisites、资源、module、显式文件、
   固定版本/许可证 provenance、已授权单作业 budget、acceptance 及数值/hook checks。
   默认区域 0/unconfigured 会阻止提交。
3. 实现 scripts/run.sh（计算节点）及 scripts/check.py（本地回收后检查）。
   所需代码和数据须列入显式文件列表。
4. 用 scnet-app validate/plan 检查，再做 scnet-hpc 只读预检和提交预览。
   保留原始钩子或验收占位条件时，planner 不给出提交命令。
5. 实现后在 SCNet 上跑一个限额案例，下载明确的结果/日志文件，核对记账与退出状态，
   再执行本地结果检查器。
6. 在 references/prerequisites_CN.md 和 references/validation_CN.md 记录栈、设备、
   运行时及数值/功能证据。

跨部署复用时可使用外部 scnet/budget 绑定。回收后通过 scnet-app record 指定原始输出及日志，
记录和副本保留在 .private/evidence/。见[验收与证据](references/verification_CN.md)。
本地产物验收及可选平台作业核对不等于硬件兼容性认证。

远端产物放进 results/。大型构建和加速器探针在调度分配的计算资源内运行。
CPU 基线和 DCU 实验分别记录。默认单节点，MPI/fan-out 需另加显式启动器、
全部预期 rank 检查及测试后再扩范围。

模板许可证仅覆盖脚手架。上游代码、模型、数据集和二进制仍遵循各自许可证。
