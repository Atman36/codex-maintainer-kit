import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


def load_contract_registry_module():
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "tools" / "contract_registry.py"
    spec = importlib.util.spec_from_file_location("contract_registry", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load contract_registry module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


contract_registry = load_contract_registry_module()


class ContractRegistryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_valid_prompt_placeholder_set_passes(self):
        prompts_dir = self.root / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        (prompts_dir / "reviewer.md").write_text(
            "Workspace: {{REPO_ROOT}}\nPRSpec: {{PRSPEC_JSON}}\nImplement: {{IMPLEMENT_JSON}}\n",
            encoding="utf-8",
        )

        issues = contract_registry.collect_contract_issues(self.root)

        self.assertEqual(issues, [])

    def test_unknown_placeholder_fails(self):
        prompts_dir = self.root / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        (prompts_dir / "bad.md").write_text(
            "Unknown: {{MISSING_PLACEHOLDER}}\n",
            encoding="utf-8",
        )

        issues = contract_registry.collect_contract_issues(self.root)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "error")
        self.assertIn("Unknown placeholder 'MISSING_PLACEHOLDER'", issues[0].message)

    def test_implement_result_json_alias_reports_warning(self):
        prompts_dir = self.root / "prompts"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        (prompts_dir / "pr_writer.md").write_text(
            "Input: {{IMPLEMENT_RESULT_JSON}}\n",
            encoding="utf-8",
        )

        issues = contract_registry.collect_contract_issues(self.root)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "warning")
        self.assertIn("IMPLEMENT_RESULT_JSON", issues[0].message)
        self.assertIn("IMPLEMENT_JSON", issues[0].message)

    def test_metadata_path_vs_object_mismatch_is_flagged(self):
        skill_dir = self.root / "skills" / "pr-factory-pr-writer"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "version": "1.0.0",
                    "inputs": [
                        {
                            "name": "IMPLEMENT_RESULT_JSON",
                            "type": "object",
                            "required": True,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        issues = contract_registry.collect_contract_issues(self.root)
        errors = [issue for issue in issues if issue.severity == "error"]
        warnings = [issue for issue in issues if issue.severity == "warning"]

        self.assertEqual(len(warnings), 1)
        self.assertIn("IMPLEMENT_RESULT_JSON", warnings[0].message)
        self.assertEqual(len(errors), 1)
        self.assertIn("must use type 'string'", errors[0].message)


if __name__ == "__main__":
    unittest.main()
