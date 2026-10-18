# 验收与私有记录

[English](verification.md) | 中文

收集证据前实现 app.json checks。数值项指定 JSON 文件/键、有限参考值及非负绝对/相对容差。
hook 项指定功能判据，scripts/check.py 须退出零并输出具名布尔结论，例如
`{"checks":{"structure":true}}`，诊断放 stderr，保留原始产物供审阅。

冻结参考和检查器，记录精确上游提交或源码归档 SHA256、许可证及依赖清单。
声明已授权单作业预算和实际 SCNet 绑定；新脚手架不默认选择集群，可编辑 app.json 或用外部绑定。

从已安装 scnet-app 根目录运行，替换示例文件名及路径：

```bash
python3 scripts/scnet_app.py record /absolute/__APP_NAME__ --results /absolute/collected --run-id pilot-001 --artifacts metrics.json raw-output.dat scheduler.out --binding /private/binding.json
```

record 建立私有输入副本、检查改写，失败/超时日志保留在本应用 .private/evidence/，拒绝复用 ID。
可选 --job-id/--remote-dir/--scnet-hpc 通过只读 job CLI 核对平台事实。
本地产物验收、调度核对及运行时证据分别报告，v0.2 不自动认证硬件兼容性。

校验值能发现编辑，不能让本机记录不可篡改。公开发布需单独审阅的摘要，
私有记录保留作业、输入及输出关联。完整格式、限制和升级说明见
[scnet-app 验证文档](https://github.com/lql341/scnet-app/blob/main/references/verification_CN.md)。
