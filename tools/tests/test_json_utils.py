import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


def load_json_utils_module():
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "tools" / "pr_factory_lib" / "json_utils.py"
    spec = importlib.util.spec_from_file_location("json_utils", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load json_utils module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


json_utils = load_json_utils_module()


class JsonUtilsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write_payload(self, relative_path: str) -> Path:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"status": "success", "value": 1}), encoding="utf-8")
        return path

    def test_parse_stage_output_accepts_direct_json(self):
        payload = json_utils.parse_stage_output('{"status":"success","value":1}')
        self.assertEqual(payload["status"], "success")
        self.assertEqual(payload["value"], 1)

    def test_parse_stage_output_accepts_plain_saved_json_path(self):
        path = self.write_payload("plain/result.json")
        payload = json_utils.parse_stage_output(f"SAVED_JSON_PATH={path}")
        self.assertEqual(payload["status"], "success")

    def test_parse_stage_output_accepts_quoted_saved_json_path_with_spaces(self):
        path = self.write_payload("with spaces/result file.json")
        payload = json_utils.parse_stage_output(f'SAVED_JSON_PATH="{path}"')
        self.assertEqual(payload["status"], "success")

    def test_parse_stage_output_accepts_unquoted_saved_json_path_with_spaces(self):
        path = self.write_payload("other spaces/result file.json")
        payload = json_utils.parse_stage_output(f"SAVED_JSON_PATH={path}")
        self.assertEqual(payload["status"], "success")

    def test_parse_stage_output_with_provenance_tracks_saved_json_source(self):
        path = self.write_payload("persisted/result.json")

        parsed = json_utils.parse_stage_output_with_provenance(f"SAVED_JSON_PATH={path}")

        self.assertEqual(parsed.source_kind, "saved_json_path")
        self.assertEqual(parsed.source_path, str(path.resolve()))
        self.assertEqual(len(parsed.source_sha256), 64)

    def test_parse_stage_output_resolves_relative_saved_json_path_from_stage_cwd(self):
        stage_cwd = self.root / "stage-cwd"
        path = self.write_payload("stage-cwd/out/result.json")

        parsed = json_utils.parse_stage_output_with_provenance("SAVED_JSON_PATH=out/result.json", cwd=stage_cwd)

        self.assertEqual(parsed.payload["value"], 1)
        self.assertEqual(parsed.source_path, str(path.resolve()))


if __name__ == "__main__":
    unittest.main()
