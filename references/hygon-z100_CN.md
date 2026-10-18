# 海光（Hygon）Z100 DCU 兼容性

[English](hygon-z100.md) | 中文

**海光（Hygon）Z100 DCU** 是一种集成目标，与海光 C86 CPU 分开。
硬件和运行时检查须与[算力、调度及打包要求](cluster-integration_CN.md)共同执行。
[固定版本超算互联网集群 profile](https://github.com/lql341/scnet-hpc/blob/0111b222087fbfe2196ca8f205aa35357e542ec8/clusters/kseshell.conf)
提供 gfx906 及显存/拓扑提示，不是实时证据，也不能外推全部海光芯片。
targets/ 只记来源，不复制连接凭证或接口。选择编译架构和依赖二进制前，检查实际分配节点。

## 适配顺序

1. **系统 ABI/环境**：记录 OS、glibc、CPU 架构/指令、Python、编译器、MPI、module，
   核对 wheel/二进制 ABI。登录节点可 import 不等于计算节点动态库就绪。
2. **DTK/运行时**：记录驱动、运行时、编译器、实际设备架构和可见性，查匹配手册，
   不假定 DTK 与某版 ROCm/CUDA 等价。不改共享驱动或全局库。
3. **最小功能路径**：先建立所需 kernel/算子和参考结果，可从 FP32 开始。
   需要时分别测 FP16/BF16、量化、Triton/自定义算子、融合注意力、集合通信，不默认支持。
4. **应用正确性**：按有依据的容差比较科学量、收敛性或模型输出，记录实际设备执行，
   拒绝意外 CPU fallback。构建、import、设备检查不等于应用正确性。
5. **资源/扩展**：小型代表输入测主机/设备峰值内存和耗时，作业前准备权重、数据和
   离线依赖。小任务未跑满设备不代表失败；多卡/多节点另行验证。

CUDA 源码转换、原生 HIP、兼容层和框架 HIP 是不同路径，应明确选择并记录。
兼容层结果不能外推原生 HIP 支持或性能。CPU 参考运行是独立实验，不静默代替 DCU。

大型 C++/HIP 构建可能需调度 CPU/内存资源。保留详细构建日志，最小化上游修改，
核对目标架构及数学/FFT/通信库。v0.1 不自动编译/安装，不固定通用 DTK/PyTorch 版本。

## 可选 PyTorch 探针

assets/probes/torch_z100.py 是计算节点 HIP FP32 小矩阵计算及参考比较探针。
需已部署 HIP PyTorch，无设备或实际架构不是 gfx906 时失败。
HIP 构建也使用 torch.cuda API，所以显式检查 torch.version.hip。
只在授权计算分配及正确框架环境内运行；本地编写不需 GPU。
通过仅证明该小探针，不代表模型/算子全面可用。非 PyTorch 科学应用需自己的运行时/
kernel 和领域检查。

## 来源和维护

- [scnet-hpc 海光指南](https://github.com/lql341/scnet-hpc/blob/0111b222087fbfe2196ca8f205aa35357e542ec8/references/hygon-dcu-development.md)
- [兼容性验证方法](https://github.com/lql341/scnet-hpc/blob/0111b222087fbfe2196ca8f205aa35357e542ec8/references/software-compatibility.md)
- [海光开发指南](https://developer.sourcefind.cn/developer-channel)
- [DTK 资源](https://developer.sourcefind.cn/dtk)

官方页面可能需浏览器/登录，本脚手架未核实其当前页面内容。部署时按实际产品、OS、
安装的 DTK 版本选择文档，不用旧示例代替当前官方配置。
