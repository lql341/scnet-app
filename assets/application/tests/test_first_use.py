import json
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import doctor  # noqa: E402


def configured_app():
    path = ROOT / "app.json"
    if path.is_file():
        app = json.loads(path.read_text(encoding="utf-8"))
    else:
        app = {
            "name": "template-test",
            "target": "hygon-z100",
            "environment": {"modules": []},
        }
    app["scnet"] = {
        "backend": "openapi",
        "cluster": "test-cluster",
        "region": "test-region",
        "queue": "test-queue",
    }
    return app


def credential_payload(ok):
    return json.dumps(
        {
            "ok": True,
            "data": {
                "ok": ok,
                "checks": [{"name": "openapi_credentials", "ok": ok}],
            },
        }
    )


class FirstUseTests(unittest.TestCase):
    def test_missing_cli_is_a_dependency_blocker(self):
        env = {
            "SCNET_OPENAPI_USER": "user-value",
            "SCNET_OPENAPI_ACCESS_KEY": "access-value",
            "SCNET_OPENAPI_SECRET_KEY": "secret-value",
        }
        with mock.patch.object(
            doctor, "load_app", return_value=configured_app()
        ), mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            doctor, "find_scnet_hpc", return_value=None
        ):
            status = doctor.probe()
        self.assertFalse(status["openapi_ready"])
        self.assertEqual(status["primary_blocker"], "scnet_hpc")
        self.assertEqual(status["dependencies"]["scnet_hpc"], "missing")

    def test_missing_cli_without_env_credentials_is_unknown_not_missing(self):
        with mock.patch.object(
            doctor, "load_app", return_value=configured_app()
        ), mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(
            doctor, "find_scnet_hpc", return_value=None
        ):
            status = doctor.probe()
        self.assertEqual(status["readiness"]["credentials"], "unknown")
        self.assertEqual(status["primary_blocker"], "scnet_hpc")

    def test_store_only_credentials_use_scnet_hpc_read_only_check(self):
        completed = mock.Mock(
            returncode=0, stdout=credential_payload(True), stderr=""
        )
        with mock.patch.object(
            doctor, "load_app", return_value=configured_app()
        ), mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(
            doctor, "find_scnet_hpc", return_value=Path("/fake/scnet.py")
        ), mock.patch.object(doctor.subprocess, "run", return_value=completed):
            status = doctor.probe()
        self.assertTrue(status["openapi_ready"])
        self.assertEqual(status["credentials"]["source"], "shared_store")
        self.assertEqual(status["credentials"]["shared_store"], "checked")

    def test_configured_region_queue_and_env_credentials(self):
        env = {
            "SCNET_OPENAPI_USER": "user-value",
            "SCNET_OPENAPI_ACCESS_KEY": "access-value",
            "SCNET_OPENAPI_SECRET_KEY": "secret-value",
        }
        with mock.patch.object(
            doctor, "load_app", return_value=configured_app()
        ), mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            doctor, "find_scnet_hpc", return_value=Path("/fake/scnet.py")
        ):
            status = doctor.probe()
        self.assertTrue(status["openapi_ready"])
        self.assertNotIn("secret-value", json.dumps(status))

    def test_missing_cli_never_reports_ready(self):
        env = {
            "SCNET_OPENAPI_USER": "user-value",
            "SCNET_OPENAPI_ACCESS_KEY": "access-value",
            "SCNET_OPENAPI_SECRET_KEY": "secret-value",
        }
        with mock.patch.object(
            doctor, "load_app", return_value=configured_app()
        ), mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            doctor, "find_scnet_hpc", return_value=None
        ):
            status = doctor.probe()
        self.assertFalse(status["openapi_ready"])
        self.assertNotEqual(status["readiness"]["credentials"], "missing")


if __name__ == "__main__":
    unittest.main()
