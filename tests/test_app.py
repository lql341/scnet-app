"""Offline behavior and optional real scnet-hpc CLI conformance; no allocation."""
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import scnet_app as app


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "science app"
        app.init_app("scnet-science", self.root, "https://example.org/science", "hygon-z100")

    def write(self, data):
        (self.root / "app.json").write_text(json.dumps(data), encoding="utf-8")

    def ready(self):
        data = app.load_app(self.root)
        data["acceptance"] = "Compare scalar result to CPU reference 1.0 with absolute tolerance 1e-6."
        data["checks"] = [{"name": "energy", "kind": "numeric", "required": True, "file": "metrics.json", "key": "energy", "ref": 1.0, "atol": 1e-6}]
        data["provenance"] = {"revision": "a" * 40, "license": "MIT"}
        data["scnet"] = {"backend": "openapi", "cluster": "kseshell", "region": "12345", "queue": "configured-queue"}
        data["stack"] = {
            "system": {"name": "centos7.6", "glibc": "2.17"},
            "toolchain": {"gcc": "16.2.0", "cmake": "4.4.3"},
            "backend": {"kind": "dcu", "runtime": "dtk", "version": "26.04", "target": "hygon-z100", "arch": "gfx906"},
            "mpi": {"vendor": "openmpi", "version": "5.0.11"},
            "framework": {"name": "none"},
            "platform": {"adapter": "scnet-openapi", "region": "12345", "cluster": "kseshell", "queue": "configured-queue"},
        }
        (self.root / data["run"]).write_text("#!/usr/bin/env bash\nexit 0\n")
        (self.root / data["check"]).write_text("raise SystemExit(0)\n")
        self.write(data)
        return data

    def test_init_complete_and_no_overwrite(self):
        for name in ("SKILL.md", "README.md", "README_CN.md", "agents/openai.yaml", "scripts/run.sh", "scripts/check.py", "LICENSE", "VERSION"):
            self.assertTrue((self.root / name).is_file(), name)
        sentinel = self.root / "keep.txt"
        sentinel.write_text("local changes")
        with self.assertRaises(app.AppError):
            app.init_app("scnet-science", self.root, "https://example.org/science", "hygon-z100")
        self.assertEqual(sentinel.read_text(), "local changes")

    def test_stock_checker_rejects_and_plan_withholds_submit(self):
        proc = subprocess.run([sys.executable, str(self.root / "scripts/check.py"), str(self.root)], capture_output=True)
        self.assertNotEqual(proc.returncode, 0)
        plan = app.plan(self.root, [sys.executable, "/hpc/scripts/scnet.py"], "/private/fresh run")
        self.assertIsNone(plan["submit"])
        self.assertFalse(plan["compute_verified"])
        self.assertFalse(plan["implementation_ready"])

    def test_metadata_does_not_claim_compute_validation(self):
        self.ready()
        with patch.object(subprocess, "run", side_effect=AssertionError("execution during planning")):
            plan = app.plan(self.root, [sys.executable, "/hpc/scripts/scnet.py"], "/private/run")
        self.assertIsNotNone(plan["submit"])
        self.assertFalse(plan["compute_verified"])
        self.assertIn("--dry-run", plan["preview"])
        for command in plan["preflight"] + plan["prepare"] + plan["upload"]:
            self.assertIn("12345", command)
            self.assertIn("openapi", command)

    def test_paths_and_resource_values_cannot_escape_contract(self):
        original = app.load_app(self.root)
        for field, value in (("run", "../outside.sh"), ("run", "/outside.sh"), ("run", "scripts/missing.sh")):
            data = json.loads(json.dumps(original))
            data[field] = value
            self.write(data)
            with self.assertRaises(app.AppError):
                app.load_app(self.root)
        for values in ({"nodes": 2}, {"cpus": True}, {"dcus_per_node": 0}, {"walltime": "00:00:00"}):
            data = json.loads(json.dumps(original))
            data["resources"].update(values)
            self.write(data)
            with self.assertRaises(app.AppError):
                app.load_app(self.root)

    def test_secrets_and_unknown_fields_are_not_configuration(self):
        data = app.load_app(self.root)
        data["scnet"]["secret_key"] = "test-fixture-not-a-secret"
        self.write(data)
        with self.assertRaisesRegex(app.AppError, "unknown fields"):
            app.load_app(self.root)

    def test_public_upstream_url_and_destination_validation(self):
        for url in ("https://user:password@example.org/app", "https://example.org/app?token=example", "https://example.org/app#fragment"):
            destination = Path(self.tmp.name) / "invalid"
            with self.assertRaises(app.AppError):
                app.init_app("scnet-test", destination, url, "hygon-z100")
            self.assertFalse(destination.exists())
        with self.assertRaises(app.AppError):
            app.init_app("scnet-test", ROOT / "assets/application/new-output", "https://example.org/app", "hygon-z100")

    def test_cpu_target_is_explicit_and_requests_no_dcu(self):
        cpu = Path(self.tmp.name) / "cpu"
        app.init_app("scnet-cpu", cpu, "https://example.org/science", "hygon-c86")
        data = app.load_app(cpu)
        self.assertEqual((data["target"], data["resources"]["dcus_per_node"], data["scnet"]["queue"]), ("hygon-c86", 0, "unconfigured"))

    def test_remote_command_quotes_paths_without_shell_evaluation(self):
        data = self.ready()
        data["environment"]["modulefiles"] = "/module dir/'quoted"
        data["environment"]["modules"] = ["compiler/dtk/site-version"]
        self.write(data)
        plan = app.plan(self.root, ["python", "/hpc/scripts/scnet.py"], "/run with spaces/$(not-executed)")
        outer = shlex.split(plan["submit"][-1])
        self.assertEqual(outer[:3], ["bash", "-l", "-c"])
        body = outer[3].splitlines()
        self.assertEqual(shlex.split(body[1]), ["cd", "/run with spaces/$(not-executed)"])
        self.assertEqual(shlex.split(body[2]), ["module", "use", data["environment"]["modulefiles"]])
        for remote in ("relative", "/a/../b", "/a\nb", "/"):
            with self.assertRaises(app.AppError):
                app.plan(self.root, ["python", "/hpc/scripts/scnet.py"], remote)

    def test_staged_artifacts_preserve_paths_and_do_not_overwrite(self):
        data = self.ready()
        (self.root / "tests/data").mkdir()
        (self.root / "tests/data/input.json").write_text('{"x":1}')
        data["files"] = ["tests/data/input.json"]
        self.write(data)
        plan = app.plan(self.root, ["python", "/hpc/scripts/scnet.py"], "/run")
        self.assertTrue(any(command[-1] == "/run/tests/data" for command in plan["upload"]))
        self.assertFalse(any("--cover" in command for command in plan["upload"]))

    @unittest.skipUnless(os.getenv("SCNET_HPC_TEST_ROOT"), "set SCNET_HPC_TEST_ROOT for real CLI conformance")
    def test_real_scnet_hpc_dry_run_contract_without_credentials(self):
        data = self.ready()
        hpc = app.hpc_cli(Path(os.environ["SCNET_HPC_TEST_ROOT"]))
        plan = app.plan(self.root, hpc, "/example/scnet-app/fresh-run")
        env = {key: value for key, value in os.environ.items() if not key.startswith("SCNET_OPENAPI_")}
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(plan["preview"], capture_output=True, encoding="utf-8", env=env, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        preview = json.loads(proc.stdout)
        self.assertEqual(preview["backend"], "openapi")
        self.assertEqual(preview["request"]["dcus"], data["resources"]["dcus_per_node"])
        self.assertIn("no request sent", preview["note"])

    def test_z100_probe_never_silently_uses_cpu(self):
        import types
        spec = importlib.util.spec_from_file_location("z100_probe", ROOT / "assets/probes/torch_z100.py")
        probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(probe)
        fake = types.SimpleNamespace(version=types.SimpleNamespace(hip=None))
        with patch.dict(sys.modules, {"torch": fake}), patch("sys.stderr"):
            self.assertEqual(probe.main(), 1)

    def test_json_output_survives_native_windows_code_pages(self):
        capture = io.StringIO()
        with redirect_stdout(capture):
            app.emit({"detail": "计算节点", "path": "C:/科学/app"})
        output = capture.getvalue()
        output.encode("ascii")
        self.assertEqual(json.loads(output)["detail"], "计算节点")

    def test_workflow_intake_run_status_and_resume_persist_attempts(self):
        state = app.workflow_intake(self.root)
        workflow = self.root / ".private" / "workflow"
        self.assertEqual(state["current_state"], "inspect")
        self.assertTrue((workflow / "state.json").is_file())
        self.assertTrue((workflow / "attempts/0001/result.json").is_file())

        result = app.workflow_run(self.root)
        self.assertEqual(result["result"]["status"], "passed")
        self.assertEqual(result["state"]["current_state"], "classify")
        self.assertEqual(result["state"]["retries_used"], 0)
        self.assertTrue((workflow / "attempts/0002/result.json").is_file())

        app.workflow_run(self.root)
        blocked = app.workflow_run(self.root)
        self.assertEqual(blocked["result"]["status"], "blocked")
        self.assertEqual(app.workflow_status(self.root)["status"], "blocked")
        self.assertEqual(app.workflow_status(self.root)["retries_used"], 1)
        explanation = app.workflow_explain_failure(self.root)
        self.assertEqual(explanation["classification"], "change_strategy")
        self.assertIn("strategy", explanation["guidance"] or "")
        app.workflow_resume(self.root)
        resumed = app.workflow_status(self.root)
        self.assertEqual(resumed["status"], "active")
        self.assertTrue(any(item.get("event") == "resume" for item in resumed["history"]))
        self.assertTrue((workflow / "attempts/0004/result.json").is_file())

    def test_workflow_rejects_duplicate_intake_and_resume_only_from_failure(self):
        app.workflow_intake(self.root)
        with self.assertRaises(app.AppError):
            app.workflow_intake(self.root)
        with self.assertRaises(app.AppError):
            app.workflow_resume(self.root)

    def test_workflow_attempt_limit_is_enforced_without_overwriting_attempts(self):
        app.workflow_intake(self.root)
        state = app.workflow_status(self.root)
        state["max_attempts"] = 1
        state["retries_used"] = 1
        (self.root / ".private/workflow/state.json").write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaisesRegex(app.AppError, "retry limit"):
            app.workflow_run(self.root)
        self.assertTrue((self.root / ".private/workflow/attempts/0001/result.json").is_file())


if __name__ == "__main__":
    unittest.main()
