# 应用集群接入清单

[English](cluster-integration.md) | 中文

对选定的 SCNet 部署完成以下事项，再声明就绪：

- app.json 绑定已开通区域、profile、队列及实时配额。确认总 CPU、每节点 DCU 和时限；
  记录内存、线程和 QoS 限制，提交前解决当前规范无法表达的必需参数。
- 记录集群认可的 module/软件前缀、精确应用和依赖版本、源码提交、构建选项、校验值
  及计算节点 ABI/运行时。安装 agent skill 不会安装远端软件。
- 分离软件、输入、每次新建的共享运行目录及结果/日志；额外文件和归档列入 app.json
  files，说明解包和离线依赖准备。planner 不递归收集目录。
- 在 Slurm 分配范围内执行，遵守设备可见性、线程限额及集群作业步启动规则并传播失败。
  大型构建使用调度资源，保留作业、区域和目录信息用于等待及取消。
- 回收明确产物及日志，核对记账和退出状态，再按参考值执行应用检查器，如实标记未测阶段。

详见 [scnet-app 接入要求](https://github.com/lql341/scnet-app/blob/main/references/cluster-integration_CN.md)
及 [scnet-hashcat 标杆对照](https://github.com/lql341/scnet-app/blob/main/references/hashcat-reference_CN.md)。
引用标杆不代表本应用已有多节点能力、科学结果正确或所选硬件兼容。
