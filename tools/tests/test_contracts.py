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

    def test_root_docs_are_scanned_for_unknown_placeholders(self):
        (self.root / "README.md").write_text(
            "Bad root placeholder: {{MISSING_ROOT_PLACEHOLDER}}\n",
            encoding="utf-8",
        )

        issues = contract_registry.collect_contract_issues(self.root)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "error")
        self.assertEqual(issues[0].path, self.root / "README.md")
        self.assertIn("Unknown placeholder 'MISSING_ROOT_PLACEHOLDER'", issues[0].message)

    def test_claude_md_is_scanned_for_stale_patterns(self):
        (self.root / "CLAUDE.md").write_text(
            "Run `pytest tools/tests/` before committing tool changes.\n",
            encoding="utf-8",
        )

        issues = contract_registry.collect_contract_issues(self.root)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "error")
        self.assertEqual(issues[0].path, self.root / "CLAUDE.md")
        self.assertIn("Stale test command", issues[0].message)

    def test_workflow_doc_is_scanned_for_unknown_placeholders(self):
        workflow_path = self.root / "skills" / "WORKFLOW.md"
        workflow_path.parent.mkdir(parents=True, exist_ok=True)
        workflow_path.write_text(
            "Workflow input: {{MISSING_WORKFLOW_PLACEHOLDER}}\n",
            encoding="utf-8",
        )

        issues = contract_registry.collect_contract_issues(self.root)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "error")
        self.assertEqual(issues[0].path, workflow_path)
        self.assertIn("Unknown placeholder 'MISSING_WORKFLOW_PLACEHOLDER'", issues[0].message)

    def test_skill_references_are_scanned_for_stale_aliases(self):
        reference_path = self.root / "skills" / "pr-factory-gatekeeper" / "references" / "input-examples.md"
        reference_path.parent.mkdir(parents=True, exist_ok=True)
        reference_path.write_text(
            "### CANDIDATES_JSON\n",
            encoding="utf-8",
        )

        issues = contract_registry.collect_contract_issues(self.root)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "error")
        self.assertEqual(issues[0].path, reference_path)
        self.assertIn("Deprecated alias 'CANDIDATES_JSON'", issues[0].message)

    def test_skill_examples_are_scanned_for_unknown_placeholders(self):
        example_path = self.root / "skills" / "pr-factory-reviewer" / "examples" / "example.md"
        example_path.parent.mkdir(parents=True, exist_ok=True)
        example_path.write_text(
            "Example input: {{MISSING_EXAMPLE_PLACEHOLDER}}\n",
            encoding="utf-8",
        )

        issues = contract_registry.collect_contract_issues(self.root)

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "error")
        self.assertEqual(issues[0].path, example_path)
        self.assertIn("Unknown placeholder 'MISSING_EXAMPLE_PLACEHOLDER'", issues[0].message)

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
