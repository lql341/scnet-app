# 应用规范 v1

[English](contract.md) | 中文

规范由 app.json、计算节点 Bash 运行钩子和本地 Python 正确性检查器组成。
[JSON Schema](../schema/app.schema.json) 是字段定义；CLI 校验其中实际使用的关键字
以及路径/目标语义，不是通用 JSON Schema 引擎。

按[集群接入要求](cluster-integration_CN.md)落实算力绑定、Slurm 分配及运行包约定，
通过 [scnet-hashcat 标杆对照](hashcat-reference_CN.md)查看具体实现参考。

| 字段 | 含义 |
| --- | --- |
| schema_version | 整数 1；不兼容变更需新 schema |
| name / upstream | 带 scnet- 前缀的名称及公开 HTTPS 项目地址，验证记录另记精确源码版本 |
| target | hygon-z100（DCU）或显式 hygon-c86（CPU），不自动回退 |
| scnet | openapi、已有集群 profile 名、明确区域 ID 和队列 |
| resources | 单节点、CPU 总数、每节点 DCU 数、正数 HH:MM:SS 时限 |
| environment | 站点 module 及可选的已存在远端绝对 modulefiles 目录，不猜通用 DTK 版本 |
| run | 在计算节点执行的相对 Bash 钩子 |
| check | 回收后在本地执行的相对 Python 检查器，参数为结果目录 |
| files | 除 app.json/run/check 外要上传的显式相对文件，保留目录结构 |
| acceptance | 应用参考结果、容差或功能成功判据 |
| provenance（v1 可选扩展） | 精确上游提交/源码归档 SHA256 及许可证，可部署计划必需 |
| budget（v1 可选扩展） | 单作业 max_nodes、max_cpus、max_dcus_per_node、max_walltime，可部署计划必需 |
| checks（v1 可选扩展） | 数值/hook 必需项及可选 holdout 元数据，record 必需 |

字段格式、外部绑定、私有记录及 v0.1 升级方式见[验收与证据](verification_CN.md)。
schema_version 保持 1，元 skill 版本为 0.2.0。缺新字段仍能读取旧包，
但部署信息不足不给 submit，缺 checks 不执行 record。

未知字段会被拒绝，凭证/接口不能成为第二套配置通道。凭证和实时资源由 scnet-hpc
管理。产物路径不能越过应用根目录，缺文件或逃逸软链接会失败。
目录/大型依赖应打包为明确归档并补应用自己的暂存/构建步骤，尚无递归依赖收集。

## 钩子职责

run.sh 在远端运行目录执行，须使用预期设备/运行时，执行有限任务，将产物写入
results/，并传播失败。不能隐藏管道错误、静默改走 CPU 或在 rank 失败后返回 0。

check.py 在本地接收回收目录参数，须拒绝缺失/损坏产物，按参考值检查应用结果，
不满足数值/功能条件时返回非零。只检查文件存在通常不足以证明科学计算正确性。
检查器有额外依赖时写清楚；元 skill CLI 自身保持只用标准库。

原始钩子含 SCNET_APP_UNIMPLEMENTED 并退出 2。标记/验收占位须替换，
绑定、来源及预算也须就绪且未超限，之后
planner 才给提交向量。移除标记不代表适配通过。
打包、API doctor、设备探针、应用正确性和性能是独立阶段。

## SCNet 接入

planner 不执行命令，只返回只读预检、mkdir/显式上传、scnet-hpc dry-run 预览和
完成钩子后的提交参数数组。调用数组时不用 shell=True；远端 Bash 正文引用路径、
module 和钩子参数。计划虽不读取密钥，仍含本地/远端路径，应私密保存。

桥接要求 scnet-hpc >=0.6.13，按 0.6.13 做协议验证。通过 --scnet-hpc、SCNET_HPC_ROOT
或 Codex skill 目录定位，不静默切 SSH，不自行认证、缓存 token 或实现文件 API。
应用与 scnet-hpc 独立版本。

远端修改前核对账户、实时队列和配额是否满足计划。每次使用新的专用远端目录；
plan 不预留路径，上传也不加 --cover。先传完声明文件再提交，固定一个区域，
只提交一次，保留作业号和目录，有限等待；超时不取消，需显式 status/cancel。

回收时按 scnet-hpc 分页取全文件列表，下载明确结果和调度 stdout/stderr，确认记账
及工作负载退出状态，再执行本地检查器。当前未实现通用 collector 或自动提交/
等待/清理闭环。未来扩展多 rank 时必须核对每个预期 rank，保留部分产物并报告失败。

## 证据和发布

记录上游版本、实际 CPU/DCU 架构、OS/glibc、DTK/框架、输入/参考值/容差、调度与
应用状态、正确性、内存/显存、耗时及范围。作业/节点/个人路径留在私有运行记录。
区分 profile 提示、本地打包、运行时/设备探针、应用正确性、性能，不无测试升级结论。

生成应用有独立版本/许可证及中英文 README。发布前核对上游再分发许可，填写实际
应用仓库的一句话安装提示语，验证安装及最小应用案例。工具不自动发布应用仓库。
