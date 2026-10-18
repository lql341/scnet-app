# 验收与私有证据

[English](verification.md) | 中文

实现应用并回收明确产物后使用本文。元 skill 仍只依赖 Python 3.8+ 标准库，不部署软件、
不提交作业，也不认证硬件。应用检查器可以有另行说明的本地依赖；它是受信任的本地应用代码，
record 不是运行任意上游脚本的沙箱。

## 结构化验收

保留供人阅读的 `acceptance`，在 app.json 增加 `checks`：

```json
[
  {"name":"energy","kind":"numeric","required":true,
   "file":"metrics.json","key":"energy","ref":1.0,"atol":0.000001,"rtol":0.0001},
  {"name":"structure","kind":"hook","required":true,
   "criterion":"验证原始输出结构及守恒约束。"}
]
```

数值文件相对回收目录，key 是 JSON 对象的顶层键，值须为有限数且不能为布尔值。
通过条件为 `abs(observed-ref) <= atol + rtol*abs(ref)`；省略的容差默认为零，
零容差支持精确计数。容差非负，参考值、容差及合成界限都须有限。
数组、收敛、统计量、单位等语义由领域检查器处理，不强行转成单一标量。

检查器第一个参数为产物副本目录，成功须退出零。hook 检查还须向 stdout 输出 JSON，
例如 `{"checks":{"structure":true}}`，缺失或 false 均失败。诊断信息放 stderr；
仅退出零不能通过 hook 检查。数值检查由 scnet-app 独立计算，不服从检查器自报的数值结论。

至少一项 `required: true`，全部必需项及检查器均成功才通过。
`holdout: true` 可标记未参与适配调优的独立案例，须说明输入/参考来源，标签不证明独立性。
部分科学软件更适合参考解、守恒或回归案例，不强制套用模型 holdout 策略。

实测前冻结判据和检查器版本，在 `provenance` 写入精确上游提交或源码归档 SHA256 及许可证。
检查器辅助文件、输入、依赖锁定清单加入显式 files，纳入源码摘要。
既有 app.json v1 继续可读，可直接增加可选字段，不删除旧 acceptance 文本。
旧描述缺预算或来源固定版本时仍可做打包校验，但不能生成可部署的 submit 命令。

## 算力绑定与预算

新脚手架使用 `unconfigured` 和区域 `0`，doctor 或提交前选择实际已开通的 profile、
区域及队列。可用外部绑定文件将可复用应用描述与部署环境分开：

```bash
cp examples/binding.example.json /private/binding.json
# 编辑实际 scnet 字段及已授权预算，区域 0 是会阻止提交的占位值。
python3 scripts/scnet_app.py plan ../scnet-myapp --binding /private/binding.json --scnet-hpc /absolute/scnet-hpc --remote-dir /absolute/remote/fresh-run
```

文件只允许且必须包含 scnet 和 budget 两个对象，仅覆盖本次命令的选择，不改写 app.json。
validate、doctor、plan、record 均支持同一 `--binding` 参数；计划中会展开明确目标。
凭证继续只交给 scnet-hpc。

原生 PowerShell 使用 Copy-Item 代替 cp，python/py -3 代替 python3，
本地文件填写实际 Windows 路径；远端路径仍为 POSIX 绝对路径。
外部绑定文件属于用户自己的部署配置。

预算限制**单作业**请求的节点、总 CPU、每节点 DCU 和时长。超限时 `submit: null` 并给原因。
它不预留配额、不累计重试次数、不知道价格，也不控制其他工具提交的作业。
实时权限、配额、调度限制及明确取消仍由基础设施负责。必需的内存、QoS、任务拓扑等
若当前适配层不能表达，仍须先明确扩展再部署。

## 记录回收产物

```bash
python3 scripts/scnet_app.py record ../scnet-myapp --results ./collected --run-id pilot-001 --artifacts metrics.json raw-output.dat scheduler.out --job-state succeeded
```

列全审阅需要的原始输出和日志，不只保留最终标量。数值检查所用文件自动加入。
路径须为相对文件，不允许符号链接或目录越界。
record 在 `APP/.private/evidence/RUN_ID/` 新建目录，拒绝复用已有 ID。
先复制指定产物、计算源码及结果摘要、计算数值判据，再在该运行目录用私有副本执行检查器。
不将原始回收目录传给检查器；源码或输入副本被改动均判失败。

记录保留检查器 stdout/stderr、失败及超时。`--checker-timeout` 范围 1–3600 秒，默认 300。
验收失败或所请求的平台核对未确认时，record 返回非零，但仍保存记录。
明确列出的日志/产物可用时，缺失数值输出可记录为失败检查。
声明 failed/cancelled/job_timeout/budget_stopped 时跳过检查器并保存失败证据。
wait_timeout 表示轮询结束、作业可能仍在运行，与终态 job_timeout 不同；
此时可以继续本地产物检查，但不推断调度成功。任何 record 命令都不取消作业。

## 独立核对 SCNet 作业

```bash
python3 scripts/scnet_app.py record ../scnet-myapp --results ./collected --run-id pilot-002 --artifacts metrics.json raw-output.dat scheduler.out --binding /private/binding.json --scnet-hpc /absolute/scnet-hpc --job-id JOB_ID --remote-dir /absolute/remote/fresh-run
```

指定 job-id 后，record 只调用基础 CLI 的只读 `--details job JOB_ID`。
scheduler 为 passed 需要作业 ID、队列、工作目录、节点、CPU、DCU 均匹配，
COMPLETED 已确认且有成功退出状态。字段不足、接口失败或记账未完成均保持 unconfirmed，
不会因手填 job-state 而变成成功。不会自动导出私有节点/账户资料。
平台核对成功时 source 为 scnet_job_checked，否则为 self_reported。

平台状态核对不证明本地产物来自该作业、其软件/环境等于当前应用，也不证明海光设备
执行过该负载；须保留私有提交/传输清单与运行时日志审阅关联。
verification 分开报告 correctness、scheduler、runtime、source。
v0.2 的 runtime 仍为 not_assessed、compute_verified 仍为 false，不提供自动硬件认证。
海光（Hygon）Z100 DCU 探针及应用正确性仍需各自的计算节点证据和审阅。

## 重读与发布证据

validate/plan 只重读记录，不执行检查器、不访问 SCNet。
源码或绑定变化计入 stale_evidence；记录校验值不符、副本缺失/被改、重算数值与记录不符
计入 invalid_evidence。摘要使用当前版本最新的有效记录，包括失败记录，不以旧成功遮盖回归。

记录按约定追加且拒绝覆盖，不声称不可篡改。校验值能发现普通编辑，不是签名，
不能阻止本机所有者同时改写数据和摘要。应用自设标签不产生独立权威性；需要独立验收时，
采用经审阅的参考及检查器，并将其与适配调优过程分开管理。

原始产物和记录默认私有并被 gitignore。自由文本、module 名、日志可能包含路径、
身份或秘密，字段白名单不能保证内容脱敏。
公开发布另行审阅的兼容摘要，包含版本、案例/参考、环境、范围和结论；
原始作业、路径及产物关联留在私有记录中。

## 设计参考

借鉴 ScienceFlow 的评估事实、准入策略及产物身份分离；其研究 worker、记忆、GPU 租约
及依赖栈不成为本项目依赖。参考固定到提交 d38150de76b45a0992bcfe175957d08004b7319a：
[GateService](https://github.com/huawei-noah/noah-research/blob/d38150de76b45a0992bcfe175957d08004b7319a/ScienceFlow/scienceflow/gates/service.py)、
[产物证据](https://github.com/huawei-noah/noah-research/blob/d38150de76b45a0992bcfe175957d08004b7319a/ScienceFlow/scienceflow/solver/lnr/global_merge/candidate_evidence.py)。
运行标杆仍为 [scnet-hashcat](hashcat-reference_CN.md)。
