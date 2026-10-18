# Hygon Z100 adaptation

English | [中文](hygon-z100_CN.md)

The priority target is Hygon **DCU Z100**, distinct from a Hygon C86 CPU. The
[versioned SCNet cluster profile](https://github.com/lql341/scnet-hpc/blob/0111b222087fbfe2196ca8f205aa35357e542ec8/clusters/kseshell.conf)
provides gfx906 and device-memory/topology hints. They are not live evidence or a
promise about every Hygon chip. targets/ records that source without copying
connection credentials/endpoints. Inspect the actual allocated node before using
architecture/compiler flags or selecting dependency binaries.

## Adaptation order

1. **Host ABI and environment**: record OS, glibc, CPU architecture/instructions,
   Python/compiler/MPI and installed modules. Check wheel/binary ABI compatibility.
   Login-node import success does not establish compute-node shared-library readiness.
2. **DTK/runtime**: record installed driver/runtime/compiler and actual device
   architecture/visibility. Use the matching official manuals, not a presumed ROCm
   or CUDA version equivalent. Do not change shared drivers or global libraries.
3. **Minimal functional path**: establish the needed kernel/operator and reference
   result, often starting with FP32. Probe FP16/BF16, quantization, Triton/custom ops,
   fused attention and collectives individually when required; do not assume support.
4. **Application correctness**: compare scientific quantities, convergence or model
   outputs to a defined reference with justified tolerance. Record actual device
   execution and reject unintended CPU fallback. Build/import/device checks alone
   are not application correctness.
5. **Resources and scale**: measure peak host/device memory and run time with a
   representative small input. Stage weights, datasets and offline dependencies
   before scheduled execution. Small work need not saturate the device. Test multiple
   devices/nodes separately after single-device correctness.

CUDA source conversion, native HIP, compatibility-layer execution and framework
HIP are distinct paths. Choose and record one. A CUDA compatibility result does
not establish native HIP support or equivalent performance. CPU reference runs
are explicit separate experiments, not silent substitutes for DCU results.

Large C++/HIP builds may need scheduled CPU/memory resources. Preserve verbose
build logs and apply minimal upstream patches; confirm target architecture and
available math/FFT/communication libraries. v0.1 does not implement an automatic
compiler/installer or choose a universal DTK/PyTorch version.

## Optional PyTorch probe

`assets/probes/torch_z100.py` is a small compute-node HIP FP32 matmul/reference probe.
It requires an already deployed HIP PyTorch and rejects absent devices or a device
architecture different from gfx906. PyTorch's torch.cuda API is also used by HIP
builds; the probe checks torch.version.hip explicitly. Run it only inside a requested
compute allocation with the right framework environment; no local GPU is needed
for authoring. Its success proves only this tiny probe, not model or operator coverage.
A non-PyTorch scientific application needs its own runtime/kernel and domain check.

## Sources and maintenance

- [scnet-hpc Hygon guidance](https://github.com/lql341/scnet-hpc/blob/0111b222087fbfe2196ca8f205aa35357e542ec8/references/hygon-dcu-development.md)
- [SCNet compatibility methodology](https://github.com/lql341/scnet-hpc/blob/0111b222087fbfe2196ca8f205aa35357e542ec8/references/software-compatibility.md)
- [Hygon developer guide](https://developer.sourcefind.cn/developer-channel)
- [DTK resources](https://developer.sourcefind.cn/dtk)

The vendor pages may require a browser/login. Their current contents were not
verified for this scaffold. Select the actual product/OS and installed DTK version
before a deployment; do not substitute old examples for current vendor guidance.
