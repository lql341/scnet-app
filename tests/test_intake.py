"""Input inspection tests for source, archive, installed and skill inputs."""
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT / "scripts"))
import scnet_intake


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "source"
        self.root.mkdir()
        (self.root / "CMakeLists.txt").write_text("project(example)\n", encoding="utf-8")
        (self.root / "LICENSE").write_text("MIT\n", encoding="utf-8")

    def test_directory_and_tar_archive_classify_as_source(self):
        direct = scnet_intake.inspect(self.root)
        self.assertEqual(direct["classification"], "source")
        archive = Path(self.tmp.name) / "source.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(self.root, arcname="example")
        result = scnet_intake.inspect(archive)
        self.assertEqual(result["input_kind"], "archive")
        self.assertEqual(result["classification"], "source")
        self.assertEqual(result["license_files"], ["LICENSE"])

    def test_zip_archive_and_existing_skill(self):
        archive = Path(self.tmp.name) / "source.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            for path in self.root.rglob("*"):
                bundle.write(path, Path("example") / path.relative_to(self.root))
        self.assertEqual(scnet_intake.inspect(archive)["classification"], "source")
        skill = Path(self.tmp.name) / "skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("# skill\n", encoding="utf-8")
        (skill / "app.json").write_text("{}\n", encoding="utf-8")
        self.assertEqual(scnet_intake.inspect(skill)["classification"], "skill")

    def test_unsafe_archive_path_is_rejected(self):
        archive = Path(self.tmp.name) / "unsafe.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("../escape", "bad")
        with self.assertRaises(ValueError):
            scnet_intake.inspect(archive)

    def test_output_is_structured_and_installed_layout_is_detected(self):
        installed = Path(self.tmp.name) / "installed"
        (installed / "bin").mkdir(parents=True)
        (installed / "bin/tool").write_text("binary\n", encoding="utf-8")
        output = Path(self.tmp.name) / "intake.json"
        result = scnet_intake.inspect(installed, output)
        self.assertEqual(result["classification"], "installed")
        self.assertEqual(json.loads(output.read_text())["intake_version"], 1)

    def test_allwmake_source_with_bin_and_lib_is_not_misclassified_as_installed(self):
        foam = Path(self.tmp.name) / "openfoam"
        (foam / "bin").mkdir(parents=True)
        (foam / "lib").mkdir()
        (foam / "Allwmake").write_text("#!/bin/sh\n", encoding="utf-8")
        (foam / "LICENSE.md").write_text("GPL-3.0-or-later\n", encoding="utf-8")
        result = scnet_intake.inspect(foam)
        self.assertEqual(result["classification"], "source")
        self.assertIn("Allwmake", result["build_markers"])
        self.assertEqual(result["license_files"], ["LICENSE.md"])
        self.assertEqual(result["adapter_hint"], "openfoam-allwmake")
        self.assertIn("ThirdParty", result["next"])


if __name__ == "__main__":
    unittest.main()
