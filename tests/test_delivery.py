"""Delivery gate tests use local records and no live SCNet allocation."""
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import scnet_app as app
import scnet_evidence as evidence


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "scnet-science"
        app.init_app("scnet-science", self.root, "https://example.org/science", "hygon-z100")

    def status(self):
        data = app.load_app(self.root)
        binding = app.resolve_binding(data)
        return app.delivery.gate(self.root, data, binding, evidence.verification(self.root, data, binding),
                                 app.implementation_ready(self.root, data), app.deployment_blocks(data, binding))

    def test_stock_scaffold_cannot_build_and_attempt_limit_is_finite(self):
        status = self.status()
        self.assertFalse(status["ready_to_build"])
        self.assertTrue(status["retry_allowed"])
        self.assertIn("runtime/app", " ".join(status["blocked_by"]))
        with self.assertRaisesRegex(ValueError, "delivery gate failed"):
            app.delivery.build(self.root, app.load_app(self.root), status, Path(self.tmp.name) / "out")
        self.assertFalse((Path(self.tmp.name) / "out").exists())

    def complete_package(self):
        data = app.load_app(self.root)
        data["scnet"] = {"backend": "openapi", "cluster": "testprofile", "region": "12345", "queue": "testqueue"}
        data["stack"] = {
            "system": {"name": "centos7.6", "glibc": "2.17"},
            "toolchain": {"gcc": "16.2.0", "cmake": "4.4.3"},
            "backend": {"kind": "dcu", "runtime": "dtk", "version": "26.04", "target": "hygon-z100", "arch": "gfx906"},
            "mpi": {"vendor": "openmpi", "version": "5.0.11"},
            "framework": {"name": "none"},
            "platform": {"adapter": "scnet-openapi", "region": "12345", "cluster": "testprofile", "queue": "testqueue"},
        }
        delivery_config = json.loads((self.root / "delivery.json").read_text())
        delivery_config["package_name"] = "science-0.1.0-gcc16_ompi5_dtk26.04_z100.tar"
        delivery_config["module_name"] = "science/0.1.0-dtk26.04-z100"
        (self.root / "delivery.json").write_text(json.dumps(delivery_config), encoding="utf-8")
        data["provenance"] = {"revision": "a" * 40, "license": "MIT"}
        data["acceptance"] = "Observed energy equals independent reference 1.0."
        data["checks"] = [{"name": "energy", "kind": "numeric", "required": True,
                           "file": "metrics.json", "key": "energy", "ref": 1.0}]
        for name, body in {
            "runtime/app/bin/science": "#!/bin/sh\necho science\n",
            "runtime/case/testcase/input.txt": "small input\n",
            "runtime/case/.check": "energy = 1.0\n",
            "runtime/case/science.slurm": "#!/bin/bash\nsrun science\n",
            "runtime/scripts/env.sh": "#!/bin/bash\nexport PATH=\"$PWD/app/bin:$PATH\"\n",
        }.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
            data["files"].append(name)
        (self.root / "scripts/run.sh").write_text("#!/bin/bash\nset -e\nruntime/app/bin/science < runtime/case/testcase/input.txt > results/output.txt\n", encoding="utf-8")
        (self.root / "scripts/check.py").write_text('import json,sys\nprint(json.dumps({"checks":{}}))\n', encoding="utf-8")
        (self.root / "app.json").write_text(json.dumps(data), encoding="utf-8")
        for name in ("README.md", "README_CN.md", "SKILL.md", "references/validation.md",
                     "references/validation_CN.md", "references/prerequisites.md",
                     "references/prerequisites_CN.md", "tests/README.md"):
            (self.root / name).write_text("Tested application guidance and evidence.\n", encoding="utf-8")
        results = Path(self.tmp.name) / "collected"
        results.mkdir()
        (results / "metrics.json").write_text('{"energy":1.0}', encoding="utf-8")
        runtime = {"target": "hygon-z100", "device_used": True, "device": "DCU observed", "runtime": "DTK observed",
                   "stack_signature": app.stack_signature(data, app.resolve_binding(data))}
        (results / "runtime.json").write_text(json.dumps(runtime), encoding="utf-8")
        return data, results

    def test_success_builds_skill_tar_and_manifest_without_private_evidence(self):
        data, results = self.complete_package()
        with patch.object(evidence, "check_job", return_value={"status": "passed", "job_id": "job1"}):
            app.record(self.root, results, "test-1", ["metrics.json", "runtime.json"],
                       job_state="succeeded", job_id="job1", remote="/scratch/test-1", hpc=["python", "fake"])
        status = self.status()
        self.assertTrue(status["ready_to_build"], status["blocked_by"])
        out = Path(self.tmp.name) / "delivery"
        built = app.delivery.build(self.root, data, status, out)
        with tarfile.open(built["runtime_tar"]) as archive:
            names = archive.getnames()
        self.assertIn("case/testcase/input.txt", names)
        self.assertIn("app/bin/science", names)
        self.assertNotIn(".private/evidence/test-1/record.json", names)
        self.assertTrue((out / "scnet-science/SKILL.md").is_file())
        self.assertTrue((out / "scnet-science/runtime/app/bin/science").is_file())
        self.assertFalse((out / "scnet-science/.private").exists())
        self.assertIn("runtime_tar", json.loads((out / "manifest.json").read_text()))
        with self.assertRaisesRegex(ValueError, "already exists"):
            app.delivery.build(self.root, data, status, out)
        config = json.loads((self.root / "delivery.json").read_text())
        config["runtime_evidence"] = "another.json"
        (self.root / "delivery.json").write_text(json.dumps(config))
        self.assertFalse(self.status()["ready_to_build"])

    def test_no_scheduler_confirmation_and_missing_runtime_block_success(self):
        _, results = self.complete_package()
        app.record(self.root, results, "test-1", ["metrics.json"], job_state="succeeded")
        status = self.status()
        self.assertFalse(status["ready_to_build"])
        self.assertIn("scheduler", " ".join(status["blocked_by"]))
        self.assertIn("runtime/device", " ".join(status["blocked_by"]))

    def test_stack_identity_must_match_module_and_tar_names(self):
        data, _ = self.complete_package()
        path = self.root / "delivery.json"
        config = json.loads(path.read_text())
        config["module_name"] = "science/0.1.0-dtk26.10-z100"
        path.write_text(json.dumps(config))
        self.assertIn("module_name does not include backend version", " ".join(self.status()["blocked_by"]))
        config["module_name"] = "science/0.1.0-dtk26.04-z100"
        config["package_name"] = "science-0.1.0-gcc16_ompi5_dtk26.10_z100.tar"
        path.write_text(json.dumps(config))
        self.assertIn("package_name does not include backend version", " ".join(self.status()["blocked_by"]))

    def test_runtime_stack_signature_must_match_accepted_binding(self):
        data, results = self.complete_package()
        runtime = json.loads((results / "runtime.json").read_text())
        runtime["stack_signature"]["backend"]["version"] = "26.10"
        (results / "runtime.json").write_text(json.dumps(runtime), encoding="utf-8")
        with patch.object(evidence, "check_job", return_value={"status": "passed", "job_id": "job1"}):
            app.record(self.root, results, "bad-stack", ["metrics.json", "runtime.json"],
                       job_state="succeeded", job_id="job1", remote="/scratch/bad-stack", hpc=["python", "fake"])
        status = self.status()
        self.assertIn("runtime/device", " ".join(status["blocked_by"]))

    def test_official_package_name_rules(self):
        path = self.root / "delivery.json"
        config = json.loads(path.read_text())
        for bad in ("science-v1.0-hygon.tar", "Science-1.0-hygon.tar", "science-1.0-hygon.zip", "science-1.0-hygon-extra.tar"):
            config["package_name"] = bad
            path.write_text(json.dumps(config))
            with self.assertRaises(ValueError):
                self.status()

    def test_plan_withholds_submit_after_recorded_attempt_limit(self):
        config = json.loads((self.root / "delivery.json").read_text())
        config["max_attempts"] = 1
        (self.root / "delivery.json").write_text(json.dumps(config))
        folder = self.root / ".private/evidence/test-1"
        folder.mkdir(parents=True)
        (folder / "record.json").write_text("{}")
        plan = app.plan(self.root, ["python", "scnet.py"], "/scratch/fresh")
        self.assertIsNone(plan["submit"])
        self.assertIn("attempt limit", " ".join(plan["blocked_by"]))


if __name__ == "__main__":
    unittest.main()
