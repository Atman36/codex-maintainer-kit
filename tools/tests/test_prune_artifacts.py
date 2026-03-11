import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


def load_prune_module():
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "tools" / "prune_artifacts.py"
    spec = importlib.util.spec_from_file_location("prune_artifacts", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load prune_artifacts module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


prune_artifacts = load_prune_module()


class PruneArtifactsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.artifact_dir = self.root / "analysis_report"
        (self.artifact_dir / "runs").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def create_run(self, run_id: str, *, age_days: int) -> Path:
        run_dir = self.artifact_dir / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "marker.txt").write_text(run_id, encoding="utf-8")
        summary_path = self.artifact_dir / f"pipeline-summary-pipeline-{run_id}.json"
        summary_path.write_text(json.dumps({"run_id": run_id}), encoding="utf-8")

        ts = prune_artifacts._utc_now().timestamp() - (age_days * 86400)
        os.utime(run_dir, (ts, ts))
        os.utime(summary_path, (ts, ts))
        return run_dir

    def test_prune_runs_deletes_only_old_runs_outside_retention_window(self):
        self.create_run("run-fresh", age_days=1)
        self.create_run("run-recent", age_days=5)
        self.create_run("run-old", age_days=45)

        report = prune_artifacts.prune_runs(
            self.artifact_dir,
            keep_last=1,
            max_age_days=30,
        )

        self.assertTrue(report["ok"])
        self.assertEqual(report["deleted_run_ids"], ["run-old"])
        self.assertTrue((self.artifact_dir / "runs" / "run-fresh").exists())
        self.assertTrue((self.artifact_dir / "runs" / "run-recent").exists())
        self.assertFalse((self.artifact_dir / "runs" / "run-old").exists())
        self.assertFalse((self.artifact_dir / "pipeline-summary-pipeline-run-old.json").exists())

    def test_prune_runs_dry_run_is_non_destructive(self):
        self.create_run("run-fresh", age_days=1)
        self.create_run("run-old", age_days=60)

        report = prune_artifacts.prune_runs(
            self.artifact_dir,
            keep_last=0,
            max_age_days=30,
            dry_run=True,
        )

        self.assertEqual(report["deleted_run_ids"], ["run-old"])
        self.assertTrue((self.artifact_dir / "runs" / "run-fresh").exists())
        self.assertTrue((self.artifact_dir / "runs" / "run-old").exists())


if __name__ == "__main__":
    unittest.main()
