import json
from pathlib import Path
import tempfile
import unittest

from blutspenden.build_site import build_site, PUBLIC_FILES


ROOT = Path(__file__).resolve().parents[1]


class SiteArtifactTests(unittest.TestCase):
    def test_packages_only_static_files_and_valid_data(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "site"
            build_site(ROOT, output)
            files = {str(p.relative_to(output)) for p in output.rglob("*") if p.is_file()}
            self.assertEqual(files, set(PUBLIC_FILES) | {"data/appointments.json", ".nojekyll"})
            self.assertEqual(json.loads((output / "data/appointments.json").read_text()),
                             json.loads((ROOT / "data/appointments.json").read_text()))
            self.assertEqual((output / "index.html").read_bytes(), (ROOT / "index.html").read_bytes())

    def test_preserves_nonempty_output(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "user-file.txt"
            marker.write_text("keep")
            with self.assertRaises(ValueError):
                build_site(ROOT, directory)
            self.assertEqual(marker.read_text(), "keep")

    def test_refuses_repository_or_ancestor_as_output(self):
        for output in (ROOT, ROOT.parent, ROOT / "assets"):
            with self.subTest(output=output), self.assertRaises(ValueError):
                build_site(ROOT, output)
