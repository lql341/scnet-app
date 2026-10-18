#!/usr/bin/env python3
"""Optional compute-node HIP/FP32 probe; requires an already deployed PyTorch."""
import json
import sys


def main():
    try:
        import torch
        if not torch.version.hip or not torch.cuda.is_available():
            raise RuntimeError("a working HIP PyTorch device is required; no CPU fallback")
        properties = torch.cuda.get_device_properties(0)
        architecture = getattr(properties, "gcnArchName", "")
        if architecture.split(":")[0] != "gfx906":
            raise RuntimeError("actual device architecture is not the Z100 profile's gfx906")
        left = torch.arange(64, dtype=torch.float32).reshape(8, 8) / 64
        right = left.T.contiguous()
        reference = left @ right
        observed = (left.to("cuda") @ right.to("cuda")).cpu()
        torch.cuda.synchronize()
        error = float((observed - reference).abs().max())
        if not torch.allclose(observed, reference, rtol=1e-4, atol=1e-5):
            raise RuntimeError("HIP FP32 result differs from CPU reference")
        print(json.dumps({"ok": True, "probe_only": True, "runtime": "hip", "architecture": architecture,
                          "framework": torch.__version__, "dtype": "float32", "max_absolute_error": error,
                          "memory_bytes": properties.total_memory}))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "probe_only": True, "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
