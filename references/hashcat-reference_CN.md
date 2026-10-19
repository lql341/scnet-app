# scnet-hashcat 候选参考

[English](hashcat-reference.md) | 中文

[scnet-hashcat](https://github.com/lql341/scnet-hashcat)当前作为以后 SCNet 应用 skill 的运行候选参考，
不是永久科学标杆。应用晋级前应先按[参考应用评选规则](../roadmap/reference-application-rubric.md)评估。
下列链接固定到已检查提交 `655ff24480c9ac6f01c7face01b7b9f91fa4d509`，更新引用前须检查差异。
它处理授权的离线密码恢复；新应用复用工程做法，并保留自己的输入、语义及正确性标准。

| 可复用要求 | 实现参考 |
| --- | --- |
| 英文默认、中文对应、区分安装与远端前置条件、一句话 agent 提示语 | [README](https://github.com/lql341/scnet-hashcat/blob/655ff24480c9ac6f01c7face01b7b9f91fa4d509/README_CN.md)及[安装说明](https://github.com/lql341/scnet-hashcat/blob/655ff24480c9ac6f01c7face01b7b9f91fa4d509/references/installation_CN.md) |
| 明确资源目标、上传输入、运行清单、限时生命周期和产物回收 | [hc.py](https://github.com/lql341/scnet-hashcat/blob/655ff24480c9ac6f01c7face01b7b9f91fa4d509/scripts/hc.py) |
| 集群 module/运行时前置条件、单协调器、srun rank、独立 rank 产物及失败传播 | [hc-node.sh](https://github.com/lql341/scnet-hashcat/blob/655ff24480c9ac6f01c7face01b7b9f91fa4d509/scripts/remote/hc-node.sh) |
| 输入切分、支持模式及应用限制 | [并行化说明](https://github.com/lql341/scnet-hashcat/blob/655ff24480c9ac6f01c7face01b7b9f91fa4d509/references/parallelization_CN.md) |
| 声明合成输入、计算节点结果及结论适用范围 | [验证记录](https://github.com/lql341/scnet-hashcat/blob/655ff24480c9ac6f01c7face01b7b9f91fa4d509/references/validation_CN.md) |
| 明确基础设施来源及维护责任 | [架构说明](https://github.com/lql341/scnet-hashcat/blob/655ff24480c9ac6f01c7face01b7b9f91fa4d509/references/architecture_CN.md)及[vendor 清单](https://github.com/lql341/scnet-hashcat/blob/655ff24480c9ac6f01c7face01b7b9f91fa4d509/scripts/vendor-manifest.json) |

## 采用标杆时保留实现边界

- scnet-app 新应用调用已安装的 scnet-hpc CLI。Hashcat 当前内置有来源版本记录的
  精简 OpenAPI 派生实现，这是已说明的实现差异，不应成为后续复制认证、文件、作业
  客户端的默认模板。
- Hashcat 有既存多节点驱动；scnet-app v1 描述限定单节点，引用该驱动不代表新增
  MPI、数组作业或 fan-out。Hashcat 不是 scnet-app 生成的应用，也未实现 app.json 规范。
- Hashcat 要求已有兼容 module，不提供通用集群安装器或二进制打包标准。
  部署遵循目标集群实际政策及[接入要求](cluster-integration_CN.md)。
- 应用分别定义正确性：hashcat 合成数据的恢复数量不能作为模拟或 AI 模型的验收标准，
  它的运行时/多节点证据也不能证明其他应用支持某硬件。

新应用发布前，验证干净环境安装，写明远端部署前置条件，审阅 SCNet 资源与 Slurm 计划，
检查失败处理，并完成最小有意义的计算节点正确性测试。未测阶段明确标为未验证。

## 将标杆映射到验收记录

内置单节点字典案例的 report.json 包含 cracked、total_hashes、expected_ranks、
reported_ranks、ok。经审阅的适配可用数值项检查 cracked == 5、total_hashes == 7，
再用 hook 检查 ok 及预期/实报 rank 一致。保留原始 rank/设备日志、summary 及私有运行清单，
不能只留数量。这些数量只适用于该合成案例，不能套到任意用户负载。见[验收规范](verification_CN.md)。
这是接入映射说明，不为 scnet-hashcat 新增 app.json 接口，也不构成 scnet-app 的新计算节点验证。
