"""Offline CI persistence tests using local Git remotes and a failed source."""

import contextlib
from datetime import datetime
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zoneinfo import ZoneInfo

from blutspenden.__main__ import run_update
from blutspenden.build_site import PUBLIC_FILES, build_site

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/persist_refresh.sh'


def git(directory, *args):
    return subprocess.run(['git', '-C', str(directory), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


class PersistenceWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / 'remote.git'
        subprocess.run(['git', 'init', '--bare', str(self.remote)],
                       check=True, capture_output=True)
        self.repo = self.root / 'checkout'
        self.repo.mkdir()
        git(self.repo, 'init', '-b', 'main')
        git(self.repo, 'config', 'user.name', 'Offline Test')
        git(self.repo, 'config', 'user.email', 'test@example.invalid')
        (self.repo / 'data').mkdir()
        for name in ['appointments.json', 'status.json']:
            shutil.copyfile(ROOT / 'data' / name, self.repo / 'data' / name)
        (self.repo / 'README.md').write_text('original')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-m', 'initial')
        git(self.repo, 'remote', 'add', 'origin', str(self.remote))
        git(self.repo, 'push', '-u', 'origin', 'main')

    def persist(self):
        return subprocess.run(['bash', str(SCRIPT)], cwd=self.repo,
                              capture_output=True, text=True)

    def change_status(self):
        path = self.repo / 'data/status.json'
        status = json.loads(path.read_text())
        status['state'] = 'error'
        status['fetched_counts'] = None
        status['error'] = 'Synthetic offline source failure'
        path.write_text(json.dumps(status))

    def test_commits_only_json_preserving_unrelated_staged_files(self):
        self.change_status()
        (self.repo / 'README.md').write_text('unrelated local work')
        git(self.repo, 'add', 'README.md')
        result = self.persist()
        self.assertEqual(result.returncode, 0, result.stderr)
        sha = result.stdout.strip()
        self.assertEqual(sha, git(self.remote, 'rev-parse', 'refs/heads/main'))
        self.assertEqual(git(self.repo, 'show', '--format=', '--name-only', sha), 'data/status.json')
        self.assertEqual(git(self.repo, 'diff', '--cached', '--name-only'), 'README.md')
        self.assertEqual(git(self.repo, 'show', 'HEAD:README.md'), 'original')

    def test_no_changes_does_not_create_empty_commit(self):
        before = git(self.repo, 'rev-parse', 'HEAD')
        result = self.persist()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), before)

    def test_remote_advance_is_never_force_overwritten(self):
        other = self.root / 'other'
        git(self.root, 'clone', '--branch', 'main', str(self.remote), str(other))
        git(other, 'config', 'user.name', 'Other Test')
        git(other, 'config', 'user.email', 'other@example.invalid')
        (other / 'README.md').write_text('concurrent change')
        git(other, 'commit', '-am', 'concurrent main update')
        git(other, 'push', 'origin', 'main')
        remote_sha = git(self.remote, 'rev-parse', 'refs/heads/main')
        self.change_status()
        self.assertNotEqual(self.persist().returncode, 0)
        self.assertEqual(git(self.remote, 'rev-parse', 'refs/heads/main'), remote_sha)

    def test_failed_fetch_status_is_persisted_and_publishable_with_old_data(self):
        class FailedClient:
            def fetch_all(self):
                raise RuntimeError('Synthetic offline source failure')
        before = (self.repo / 'data/appointments.json').read_bytes()
        old = json.loads(before)
        now = datetime.fromisoformat(old['last_successful_fetch']).astimezone(ZoneInfo('Europe/Vienna'))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(run_update(self.repo / 'data', FailedClient(), now), 1)
        self.assertEqual((self.repo / 'data/appointments.json').read_bytes(), before)
        result = self.persist()
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in PUBLIC_FILES:
            target = self.repo / name
            if target.exists():
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        output = self.root / 'site'
        build_site(self.repo, output)
        self.assertEqual(json.loads((output / 'data/appointments.json').read_text()), old)
        self.assertEqual(json.loads((output / 'data/status.json').read_text())['state'], 'error')
