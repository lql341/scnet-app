"""CPU quick-build vertical slice tests; no SCNet allocation."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "scripts/scnet_app.py"


class QuickBuildTests(unittest.TestCase):
    def run_build(self, fixture, name="scnet-smoke"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        output = Path(tmp.name) / name
        proc = subprocess.run(
            [sys.executable, str(CLI), "quick-build", str(ROOT / "tests/fixtures" / fixture),
             "--output", str(output), "--name", name, "--upstream", "https://example.org/smoke"],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return output, json.loads(proc.stdout)

    def test_cmake_build_generates_runnable_cpu_skill_and_tar(self):
        output, result = self.run_build("cpu-cmake")
        self.assertEqual(result["build_system"], "cmake")
        self.assertFalse(result["compute_verified"])
        self.assertEqual(result["smoke"], "passed")
        self.assertTrue((output / "runtime/app/bin" / result["binary"]).is_file())
        self.assertTrue((output / "smoke-0.1.0-cpu.tar").is_file())
        self.assertEqual(subprocess.run(
            [sys.executable, str(output / "scripts/check.py"), str(output / "results")],
            capture_output=True, text=True,
        ).returncode, 0)
        data = json.loads((output / "app.json").read_text(encoding="utf-8"))
        self.assertEqual(data["target"], "hygon-c86")
        self.assertEqual(data["resources"]["dcus_per_node"], 0)
        self.assertEqual(data["provenance"]["revision"].__len__(), 64)

    def test_make_build_is_detected(self):
        output, result = self.run_build("cpu-make", "scnet-make")
        self.assertEqual(result["build_system"], "make")
        self.assertTrue((output / "runtime/app/bin" / result["binary"]).is_file())

    def test_bad_source_and_existing_output_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "bad"
            source.mkdir()
            output = Path(tmp) / "out"
            proc = subprocess.run(
                [sys.executable, str(CLI), "quick-build", str(source), "--output", str(output),
                 "--name", "scnet-bad", "--upstream", "https://example.org/bad"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(proc.returncode, 0)
            output.mkdir()
            (output / "sentinel").write_text("keep", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(CLI), "quick-build", str(ROOT / "tests/fixtures/cpu-cmake"),
                 "--output", str(output), "--name", "scnet-bad", "--upstream", "https://example.org/bad"],
                capture_output=True, text=True,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertEqual((output / "sentinel").read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
