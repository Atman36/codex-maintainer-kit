import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


def load_eval_module():
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "tools" / "eval_stage_compat.py"
    spec = importlib.util.spec_from_file_location("eval_stage_compat", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load eval_stage_compat module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


eval_stage_compat = load_eval_module()


class EvalStageCompatTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write_payload(self, name: str, payload: dict) -> Path:
        path = self.root / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_evaluate_stage_payloads_reports_success(self):
        payload = {
            "schema_version": "1.0",
            "id": "scout-id",
            "stage": "scout",
            "status": "success",
            "summary": "ok",
            "started_at": "2026-01-01T00:00:00Z",
            "finished_at": "2026-01-01T00:00:00Z",
            "exit_code": 0,
            "stdout": "",
            "stderr": "",
            "artifacts": [],
            "metrics": {
                "duration_ms": 1,
                "cost_usd": 0.0,
                "tokens_in": 0,
                "tokens_out": 0,
            },
            "errors": [],
            "warnings": [],
            "data": {"candidates": [{"id": "cand-1"}]},
        }
        path = self.write_payload("scout.json", payload)

        report = eval_stage_compat.evaluate_stage_payloads([("scout", path)])

        self.assertTrue(report["ok"])
        self.assertEqual(report["results"][0]["error"], "")

    def test_evaluate_stage_payloads_reports_schema_failure(self):
        path = self.write_payload("bad-scout.json", {"stage": "scout"})

        report = eval_stage_compat.evaluate_stage_payloads([("scout", path)])

        self.assertFalse(report["ok"])
        self.assertIn("ExecutionResult validation", report["results"][0]["error"])


if __name__ == "__main__":
    unittest.main()
