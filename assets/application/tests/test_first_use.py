import json
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import doctor  # noqa: E402


class FirstUseTests(unittest.TestCase):
    def test_missing_credentials_is_actionable(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(
            doctor, "find_scnet_hpc", return_value=None
        ):
            status = doctor.probe()
        self.assertFalse(status["openapi_ready"])
        self.assertEqual(status["primary_blocker"], "credentials")
        self.assertEqual(status["readiness"]["remote"], "unknown")

    def test_configured_region_and_queue_with_credentials(self):
        app = json.loads((ROOT / "app.json").read_text(encoding="utf-8"))
        app["scnet"] = {
            "backend": "openapi",
            "cluster": "test-cluster",
            "region": "test-region",
            "queue": "test-queue",
        }
        env = {
            "SCNET_OPENAPI_USER": "user-value",
            "SCNET_OPENAPI_ACCESS_KEY": "access-value",
            "SCNET_OPENAPI_SECRET_KEY": "secret-value",
        }
        with mock.patch.object(doctor, "load_app", return_value=app), mock.patch.dict(
            os.environ, env, clear=True
        ), mock.patch.object(doctor, "find_scnet_hpc", return_value=None):
            status = doctor.probe()
        self.assertTrue(status["openapi_ready"])
        self.assertNotIn("secret-value", json.dumps(status))


if __name__ == "__main__":
    unittest.main()
