"""Behavior tests for budgets, local evidence and the SCNet read-only boundary."""
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import scnet_app as app
import scnet_evidence as evidence


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "app"
        app.init_app("scnet-test", self.root, "https://example.org/science", "hygon-z100")
        self.results = Path(self.tmp.name) / "results"
        self.results.mkdir()
        self.write_result("metrics.json", {"energy": 1.0})

    def write_result(self, name, value):
        (self.results / name).write_text(json.dumps(value), encoding="utf-8")

    def save(self, data):
        (self.root / "app.json").write_text(json.dumps(data), encoding="utf-8")

    def ready(self, checker="raise SystemExit(0)\n"):
        data = app.load_app(self.root)
        data["acceptance"] = "Compare energy to the independent CPU reference."
        data["checks"] = [{"name": "energy", "kind": "numeric", "required": True, "file": "metrics.json", "key": "energy", "ref": 1.0, "atol": 1e-6}]
        data["provenance"] = {"revision": "a" * 40, "license": "MIT"}
        data["scnet"] = {"backend": "openapi", "cluster": "test-profile", "region": "12345", "queue": "test-queue"}
        data["stack"] = {
            "system": {"name": "centos7.6", "glibc": "2.17"},
            "toolchain": {"gcc": "16.2.0", "cmake": "4.4.3"},
            "backend": {"kind": "dcu", "runtime": "dtk", "version": "26.04", "target": "hygon-z100", "arch": "gfx906"},
            "mpi": {"vendor": "openmpi", "version": "5.0.11"},
            "framework": {"name": "none"},
            "platform": {"adapter": "scnet-openapi", "region": "12345", "cluster": "test-profile", "queue": "test-queue"},
        }
        (self.root / "scripts/run.sh").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        (self.root / "scripts/check.py").write_text(checker, encoding="utf-8")
        self.save(data)
        return data

    def record(self, name="test", **kwargs):
        return app.record(self.root, self.results, name, ["metrics.json"], **kwargs)

    def test_new_scaffold_has_no_implicit_cluster_binding(self):
        data = app.load_app(self.root)
        self.assertEqual(data["scnet"]["region"], "0")
        plan = app.plan(self.root, ["python", "scnet.py"], "/run")
        self.assertIsNone(plan["submit"])
        self.assertTrue(any("SCNet" in reason for reason in plan["blocked_by"]))

    def test_each_budget_limit_blocks_submission(self):
        base = self.ready()
        for field, maximum in (("cpus", 4), ("dcus_per_node", 0), ("walltime", "00:01:00")):
            data = copy.deepcopy(base)
            data["budget"]["max_" + field] = maximum
            self.save(data)
            plan = app.plan(self.root, ["python", "scnet.py"], "/run")
            self.assertIsNone(plan["submit"])
            self.assertTrue(any(field in reason for reason in plan["blocked_by"]))

    def test_external_binding_is_explicit_and_does_not_rewrite_descriptor(self):
        data = self.ready()
        binding = app.resolve_binding(data)
        binding["scnet"]["region"] = "23456"
        path = Path(self.tmp.name) / "binding.json"
        path.write_text(json.dumps(binding))
        original = (self.root / "app.json").read_bytes()
        plan = app.plan(self.root, ["python", "scnet.py"], "/run", path)
        self.assertIn("23456", plan["submit"])
        self.assertEqual((self.root / "app.json").read_bytes(), original)
        binding["secret"] = "fixture"
        path.write_text(json.dumps(binding))
        with self.assertRaises(ValueError):
            app.resolve_binding(data, path)

    def test_legacy_v1_still_loads_but_missing_deployment_facts_block_plan(self):
        data = self.ready()
        for key in ("checks", "budget", "provenance"):
            data.pop(key)
        self.save(data)
        self.assertEqual(app.load_app(self.root)["schema_version"], 1)
        self.assertIsNone(app.plan(self.root, ["python", "scnet.py"], "/run")["submit"])

    def test_offline_correctness_is_self_reported_and_never_hardware_certification(self):
        self.ready()
        self.write_result("env.json", {"architecture": "gfx906", "dcu_count": 1})
        status = self.record(job_state="succeeded")
        self.assertEqual(status["verification"]["correctness"], "passed")
        self.assertEqual(status["verification"]["source"], "self_reported")
        self.assertEqual(status["verification"]["runtime"], "not_assessed")
        self.assertFalse(status["compute_verified"])

    def test_numeric_failure_cannot_be_overruled_by_successful_checker(self):
        self.ready()
        self.write_result("metrics.json", {"energy": 9.0})
        self.assertEqual(self.record()["verification"]["correctness"], "failed")

    def test_checker_mutation_fails_and_original_results_are_preserved(self):
        self.ready("from pathlib import Path\nimport sys\n(Path(sys.argv[1])/'metrics.json').write_text('{\"energy\":1.0}')\n")
        self.write_result("metrics.json", {"energy": 9.0})
        self.assertEqual(self.record()["verification"]["correctness"], "failed")
        self.assertEqual(json.loads((self.results / "metrics.json").read_text())["energy"], 9.0)

    def test_record_refuses_reuse_and_keeps_raw_evidence_private(self):
        self.ready()
        done = self.record()
        self.assertIn(".private", done["evidence"])
        self.assertTrue((Path(done["evidence"]).parent / "artifacts/metrics.json").is_file())
        with self.assertRaises(FileExistsError):
            self.record()

    def test_edited_verdict_is_invalid_even_when_source_hashes_match(self):
        data = self.ready()
        self.write_result("metrics.json", {"energy": 9.0})
        path = Path(self.record()["evidence"])
        entry = json.loads(path.read_text())
        entry["checks"][0]["passed"] = True
        path.write_text(json.dumps(entry))
        status = evidence.verification(self.root, data, app.resolve_binding(data))
        self.assertEqual(status["invalid_evidence"], 1)
        self.assertEqual(status["verification"]["correctness"], "not_recorded")

    def test_source_and_binding_changes_make_old_records_stale(self):
        data = self.ready()
        self.record()
        binding = app.resolve_binding(data)
        binding["scnet"]["queue"] = "other"
        self.assertEqual(evidence.verification(self.root, data, binding)["stale_evidence"], 1)
        (self.root / data["run"]).write_text("#!/usr/bin/env bash\nexit 1\n")
        self.assertEqual(evidence.verification(self.root, data, app.resolve_binding(data))["stale_evidence"], 1)

    def test_changed_recorded_results_are_invalid(self):
        data = self.ready()
        path = Path(self.record()["evidence"])
        (path.parent / "artifacts/metrics.json").write_text('{"energy":9.0}')
        self.assertEqual(evidence.verification(self.root, data, app.resolve_binding(data))["invalid_evidence"], 1)

    def test_checker_timeout_is_recorded_as_failure(self):
        self.ready()
        with patch.object(evidence.subprocess, "run", side_effect=subprocess.TimeoutExpired("checker", 1)):
            done = self.record(timeout=1)
        entry = json.loads(Path(done["evidence"]).read_text())
        self.assertEqual(entry["checker_error"], "checker_timeout")
        self.assertEqual(done["verification"]["correctness"], "failed")

    def test_hook_checks_require_named_true_verdicts(self):
        data = self.ready()
        data["checks"] = [{"name": "structure", "kind": "hook", "required": True, "criterion": "Validate the raw output structure."}]
        self.save(data)
        self.assertEqual(self.record("empty")["verification"]["correctness"], "failed")
        (self.root / data["check"]).write_text('print(\'{"checks":{"structure":true}}\')\n')
        self.assertEqual(self.record("named")["verification"]["correctness"], "passed")

    def test_checks_reject_nonfinite_duplicate_and_wrong_tolerances(self):
        base = self.ready()
        for checks in ([base["checks"][0]] * 2, [{**base["checks"][0], "ref": float("nan")}],
                       [{**base["checks"][0], "atol": -1}], [{**base["checks"][0], "ref": 1e308, "rtol": 1e308}],
                       [{**base["checks"][0], "required": False}]):
            data = copy.deepcopy(base)
            data["checks"] = checks
            self.save(data)
            with self.assertRaises(ValueError):
                app.load_app(self.root)

    def test_relative_tolerance_exact_counts_and_optional_holdout(self):
        data = self.ready()
        data["checks"][0].update(atol=0, rtol=0.01, holdout=False)
        self.save(data)
        self.write_result("metrics.json", {"energy": 1.005})
        self.assertEqual(self.record("relative")["verification"]["correctness"], "passed")
        data["checks"][0]["rtol"] = 0
        self.save(data)
        self.assertEqual(self.record("exact")["verification"]["correctness"], "failed")

    def test_fake_cpu_environment_never_certifies_hygon(self):
        self.ready()
        self.write_result("metrics.json", {"energy": 1.0, "architecture": "aarch64", "dcu_count": 0})
        self.assertFalse(self.record()["compute_verified"])

    def test_scheduler_confirmation_requires_matching_history_and_allocation(self):
        data = self.ready()
        binding = app.resolve_binding(data)
        job = {"job_id": "42", "state": "COMPLETED", "source": "history", "queue": "test-queue", "work_dir": "/run", "nodes": 1, "cpus": 8, "dcus": 1, "exit_code": "0:0"}
        with patch.object(evidence.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, json.dumps(job), "")) as call:
            result = evidence.check_job(["python", "scnet.py", "--details", "job", "42"], "42", "/run", data, binding)
        self.assertEqual(result["status"], "passed")
        self.assertNotIn("submit", call.call_args.args[0])
        for change in ({"source": "realtime"}, {"dcus": None}, {"work_dir": "/other"}, {"state": "FINALIZING"}, {"exit_code": "1:0"}):
            with patch.object(evidence.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, json.dumps({**job, **change}), "")):
                self.assertEqual(evidence.check_job(["job"], "42", "/run", data, binding)["status"], "unconfirmed")

    def test_wait_timeout_is_distinct_from_terminal_job_timeout(self):
        self.ready()
        self.assertEqual(self.record("wait", job_state="wait_timeout")["verification"]["correctness"], "passed")
        self.assertEqual(self.record("terminal", job_state="job_timeout")["verification"]["correctness"], "failed")

    def test_latest_current_failure_is_not_hidden_by_an_older_pass(self):
        data = self.ready()
        self.record("pass")
        self.write_result("metrics.json", {"energy": 9.0})
        self.record("fail")
        status = evidence.verification(self.root, data, app.resolve_binding(data))
        self.assertEqual(status["verification"]["correctness"], "failed")
        self.assertEqual(status["verification"]["run_id"], "fail")

    def test_record_job_check_is_read_only_and_keeps_correctness_separate(self):
        self.ready()
        job = {"status": "passed", "job_id": "42"}
        with patch.object(evidence, "check_job", return_value=job) as check:
            done = self.record(hpc=["python", "scnet.py"], job_id="42", remote="/run")
        argv = check.call_args.args[0]
        self.assertEqual(argv[-3:], ["--details", "job", "42"])
        self.assertIn("12345", argv)
        self.assertNotIn("submit", argv)
        self.assertEqual(done["verification"]["scheduler"], "passed")
        self.assertEqual(done["verification"]["correctness"], "passed")
        self.assertEqual(done["verification"]["source"], "scnet_job_checked")
        self.assertFalse(done["compute_verified"])

    def test_cli_failure_keeps_record_and_returns_nonzero(self):
        self.ready()
        self.write_result("metrics.json", {"energy": 9.0})
        output = io.StringIO()
        with redirect_stdout(output):
            code = app.main(["record", str(self.root), "--results", str(self.results), "--run-id", "cli-fail", "--artifacts", "metrics.json"])
        self.assertEqual(code, 1)
        self.assertTrue(Path(json.loads(output.getvalue())["evidence"]).is_file())

    def test_failed_job_can_record_logs_without_missing_numeric_outputs(self):
        self.ready()
        (self.results / "metrics.json").unlink()
        (self.results / "scheduler.out").write_text("application failed before output")
        done = app.record(self.root, self.results, "partial", ["scheduler.out"], job_state="failed")
        entry = json.loads(Path(done["evidence"]).read_text())
        self.assertEqual(entry["missing_check_files"], ["metrics.json"])
        self.assertEqual(done["verification"]["correctness"], "failed")


if __name__ == "__main__":
    unittest.main()
