# SCNet 集群接入

[English](cluster-integration.md) | 中文

编写应用时与[应用规范](contract_CN.md)一起使用。本文规定本项目的交付约定；
部署前须核实目标集群的软件/module、存储、调度和再分发政策，
不假定存在适用于全部 SCNet 集群的二进制包格式。

## 算力绑定与 Slurm

| 应用声明 | 基础设施行为及核查事项 |
| --- | --- |
| scnet.cluster / region / queue | 选择已有 profile 和已开通区域/队列，通过 scnet-hpc doctor/resource-summary 确认权限和配额 |
| resources.nodes | v1 限定一个节点；分配多个节点本身不会自动在额外节点启动工作 |
| resources.cpus | 总 CPU 请求，传给 scnet-hpc --cpus，不直接等同于 Slurm --cpus-per-task 或进程/线程数量 |
| resources.dcus_per_node | 传给 scnet-hpc --dcus，设备/GRES 映射和绑定由集群配置决定 |
| resources.walltime | 正数 HH:MM:SS，传给 --walltime，核对实际队列时限 |
| environment / run | 在已分配计算作业内加载声明的 module，在独立共享运行目录执行 Bash 钩子 |

应用走 SCNet/scnet-hpc 提交路径，不再构建一套 sbatch 客户端，预览须符合目标集群政策。
当前描述没有内存、account/QoS、任务/线程拓扑或容器字段。若这些是部署必需项且
现有 profile/backend 无法提供，应先停止部署，明确扩展规范和适配层并验证后再声明支持，
不能把缺失的资源请求藏进 shell 命令。

钩子须遵守分配后的设备可见性，线程数量在资源预算内。需要作业步时使用集群要求的
srun/MPI 启动方式，避免嵌套申请或提交；v1 不提供通用 MPI 启动器。
大型构建、基准及加速器探针须使用调度分配的计算资源，应用计算不在登录节点运行。

提交成功不代表作业完成。保留区域、作业 ID 和运行目录；仅提交一次，有限等待，
核对状态、记账与应用退出码。轮询超时不会取消作业，须提供明确查询和取消方法。
包装器和管道须传播非零退出码，扩展分布式执行时检查全部预期 rank。

Slurm [sbatch 文档](https://slurm.schedmd.com/sbatch.html)区分提交与分配，
并说明不会代用户传输输入文件；[srun 文档](https://slurm.schedmd.com/srun.html)
说明作业步及资源绑定。实际启动规则以已安装版本和集群配置为准。

## 两类包与可复现部署

**Agent skill 包**包含 SKILL.md、元数据、中英文安装使用说明、app.json、钩子、
测试和验证记录。安装它只注册 agent 指令，不会在集群安装科学软件。

**集群运行包**包含或引用计算钩子所需的软件构建、依赖与输入。每个应用需要：

1. 记录上游提交、补丁、许可证、构建选项、OS/glibc/CPU ABI、框架/编译器/MPI
   及所选加速器运行时。锁定依赖版本，为分发归档记录校验值，按目标集群支持的
   module/软件包约定说明如何重建和验证。
2. 优先使用已有且验证过的集群 module；否则说明获准的用户软件前缀及 modulefile，
   或明确支持的容器路径。脚手架不自动实现容器、module 发布或远端安装，
   不修改共享驱动或系统库。
3. 分离有版本的软件、只读输入、每次新建的可写运行目录和结果/日志。
   使用计算节点可见的共享绝对路径；需要 scratch 时说明暂存及回写。
   不依赖登录 shell 的当前目录或未记录的 PATH/动态库改动。
4. 提交前传输声明的文件。planner 自带 app.json/run/check，其他代码、输入和归档
   写入 files。不支持目录或递归依赖发现，须显式打包并由应用实现安全解包/准备。
   不假设计算节点可联网，不在每个作业内临时安装未锁定依赖。
5. 输出进入 results/，保留调度及应用日志，缺失产物按失败处理。
   下载明确产物后按参考值/容差运行本地正确性检查器。
   秘密和私有运行数据不进入公开仓库或兼容报告。

选用海光（Hygon）Z100 DCU / DTK 时继续执行[运行时检查](hygon-z100_CN.md)。
[scnet-hashcat](hashcat-reference_CN.md)提供具体生命周期与打包参考。
描述和路径校验成功，不证明集群政策合规、软件部署完成、科学正确性或性能。
