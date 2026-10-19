"""Offline execution tests for the level-A package standard runner."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import scnet_level_a as level_a


class LevelATests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "fixture"
        self._write_fixture("hygon-c86")

    def _write_fixture(self, target, declaration=None):
        self.root.mkdir(parents=True, exist_ok=True)
        validation = {"criterion_version": "level-a-v1", "standard_suites": ["level-a"]}
        if declaration:
            validation["device_evidence"] = declaration
        data = {
            "name": "scnet-level-a-fixture",
            "target": target,
            "run": "scripts/run.sh",
            "check": "scripts/check.py",
            "validation": validation,
        }
        (self.root / "app.json").write_text(json.dumps(data), encoding="utf-8")
        (self.root / "scripts").mkdir(parents=True, exist_ok=True)
        (self.root / "scripts/run.sh").write_text(
            """#!/usr/bin/env bash
set -u
if [ "${SCNET_LEVEL_A_FORCE_FAILURE:-0}" = 1 ]; then
  echo "forced application failure" >&2
  exit 7
fi
if [ "${SCNET_LEVEL_A_BAD_INPUT:-0}" = 1 ]; then
  echo "bad input: fixture rejected" >&2
  exit 2
fi
mkdir -p results
printf 'ok\\n' > results/output.txt
printf 'device: cpu fixture\\n' > results/device.log
""",
            encoding="utf-8",
        )
        (self.root / "scripts/check.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
        runtime_scripts = self.root / "runtime/scripts"
        runtime_scripts.mkdir(parents=True, exist_ok=True)
        (runtime_scripts / "env.sh").write_text(
            """#!/usr/bin/env bash
SCRIPTDIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null && cd .. && pwd)
export FIXTURE_RUNTIME_ROOT="$SCRIPTDIR"
""",
            encoding="utf-8",
        )
        (self.root / "runtime/case/testcase").mkdir(parents=True, exist_ok=True)
        (self.root / "runtime/case/testcase/input.txt").write_text("fixture\n", encoding="utf-8")

    def test_cpu_fixture_passes_all_applicable_checks_and_writes_evidence(self):
        output = Path(self.tmp.name) / "level-a.json"
        result = level_a.run(self.root, output)
        self.assertTrue(result["passed"], result)
        statuses = {item["id"]: item["status"] for item in result["checks"]}
        self.assertEqual(statuses["device_evidence"], "not_applicable")
        self.assertTrue(all(status in ("passed", "not_applicable") for status in statuses.values()))
        self.assertEqual(json.loads(output.read_text())["standard"], "level-a-v1")

    def test_dcu_device_evidence_is_declarative_and_required(self):
        self._write_fixture("hygon-z100", {"artifact": "device.log", "patterns": ["device: cpu fixture"]})
        result = level_a.run(self.root)
        self.assertTrue(result["passed"], result)
        self.assertEqual(next(item for item in result["checks"] if item["id"] == "device_evidence")["status"], "passed")

        self._write_fixture("hygon-z100", {"artifact": "device.log", "patterns": ["Backend Device ID"]})
        result = level_a.run(self.root)
        self.assertFalse(result["passed"])
        row = next(item for item in result["checks"] if item["id"] == "device_evidence")
        self.assertEqual(row["status"], "failed")

    def test_runner_exposes_negative_paths_as_failures_when_hook_ignores_them(self):
        (self.root / "scripts/run.sh").write_text(
            "#!/usr/bin/env bash\nmkdir -p results; echo ok > results/output.txt\n",
            encoding="utf-8",
        )
        result = level_a.run(self.root)
        self.assertFalse(result["passed"])
        statuses = {item["id"]: item["status"] for item in result["checks"]}
        self.assertEqual(statuses["exit_status"], "failed")
        self.assertEqual(statuses["bad_input"], "failed")

    def test_cli_returns_nonzero_and_json_for_failed_standard(self):
        self._write_fixture("hygon-z100", {"artifact": "missing.log", "patterns": ["DCU"]})
        output = Path(self.tmp.name) / "result.json"
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts/scnet_level_a.py"), str(self.root), "--output", str(output)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 1)
        payload = json.loads(proc.stdout)
        self.assertFalse(payload["passed"])
        self.assertTrue(output.is_file())


if __name__ == "__main__":
    unittest.main()
