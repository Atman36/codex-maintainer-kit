import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
QUALITY_GATE_PATH = REPO_ROOT / "tools" / "quality_gate.py"


def run_cmd(args, cwd):
    subprocess.run(args, cwd=str(cwd), check=True, capture_output=True, text=True)


class QualityGateCliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir(parents=True, exist_ok=True)
        run_cmd(["git", "init", "-b", "main"], cwd=self.repo)
        run_cmd(["git", "config", "user.email", "test@example.com"], cwd=self.repo)
        run_cmd(["git", "config", "user.name", "Test User"], cwd=self.repo)

        (self.repo / "planned.txt").write_text("planned\n", encoding="utf-8")
        (self.repo / "tracked.txt").write_text("tracked\n", encoding="utf-8")
        run_cmd(["git", "add", "planned.txt", "tracked.txt"], cwd=self.repo)
        run_cmd(["git", "commit", "-m", "init"], cwd=self.repo)

        self.prspec_path = self.root / "prspec.json"
        self.prspec_path.write_text(
            json.dumps(
                {
                    "files_touched": ["planned.txt"],
                    "risk": "low",
                    "test_plan": ["python3 -m unittest tools/tests/test_quality_gate.py"],
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        self._tmp.cleanup()

    def run_quality_gate(self, *extra_args):
        cmd = [
            sys.executable,
            str(QUALITY_GATE_PATH),
            "--repo",
            str(self.repo),
            "--prspec",
            str(self.prspec_path),
            "--enforce-files-touched",
            "--json",
            *extra_args,
        ]
        return subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))

    def test_autoclean_untracked_unplanned_file(self):
        unplanned = self.repo / "untracked.txt"
        unplanned.write_text("temp\n", encoding="utf-8")

        result = self.run_quality_gate("--autoclean-unplanned")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertFalse(unplanned.exists())
        self.assertEqual(report["files_touched_check"]["autocleaned_paths"], ["untracked.txt"])
        self.assertEqual(report["files_touched_check"]["unplanned_paths"], [])
        self.assertEqual(report["files_touched_check"]["autoclean_errors"], [])

    def test_autoclean_tracked_unplanned_file(self):
        tracked = self.repo / "tracked.txt"
        tracked.write_text("modified\n", encoding="utf-8")

        result = self.run_quality_gate("--autoclean-unplanned")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["ok"])
        self.assertEqual(tracked.read_text(encoding="utf-8"), "tracked\n")
        status = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True,
            text=True,
            cwd=str(self.repo),
            check=True,
        )
        self.assertEqual(status.stdout.strip(), "")
        self.assertEqual(report["files_touched_check"]["autocleaned_paths"], ["tracked.txt"])
        self.assertEqual(report["files_touched_check"]["unplanned_paths"], [])
        self.assertEqual(report["files_touched_check"]["autoclean_errors"], [])

    def test_enforce_files_touched_without_autoclean_still_reports_unplanned(self):
        unplanned = self.repo / "untracked.txt"
        unplanned.write_text("temp\n", encoding="utf-8")

        result = self.run_quality_gate()

        self.assertEqual(result.returncode, 2, msg=result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertTrue(unplanned.exists())
        self.assertFalse(report["files_touched_check"]["autoclean_applied"])
        self.assertEqual(report["files_touched_check"]["autocleaned_paths"], [])
        self.assertEqual(report["files_touched_check"]["unplanned_paths"], ["untracked.txt"])


if __name__ == "__main__":
    unittest.main()
