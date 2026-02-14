import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


def load_validate_skills_module():
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "tools" / "validate_skills.py"
    spec = importlib.util.spec_from_file_location("validate_skills", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load validate_skills module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validate_skills = load_validate_skills_module()


class ValidateSkillsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "skills").mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _create_skill(
        self,
        name: str,
        skill_md: str | None,
        metadata_json: str | None,
    ) -> None:
        skill_dir = self.root / "skills" / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        if skill_md is not None:
            (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
        if metadata_json is not None:
            (skill_dir / "metadata.json").write_text(metadata_json, encoding="utf-8")

    def test_validate_skills_passes_for_valid_skill(self):
        self._create_skill(
            name="valid-skill",
            skill_md=(
                "---\n"
                "name: valid-skill\n"
                "description: test skill\n"
                "---\n\n"
                "# Valid Skill\n"
            ),
            metadata_json='{"version": "1.0.0"}',
        )

        exit_code = validate_skills.validate_skills(self.root)
        self.assertEqual(exit_code, 0)

    def test_validate_skills_fails_without_metadata(self):
        self._create_skill(
            name="missing-meta",
            skill_md=(
                "---\n"
                "name: missing-meta\n"
                "description: test skill\n"
                "---\n\n"
                "# Missing Metadata\n"
            ),
            metadata_json=None,
        )

        exit_code = validate_skills.validate_skills(self.root)
        self.assertEqual(exit_code, 1)

    def test_validate_skills_fails_without_frontmatter(self):
        self._create_skill(
            name="missing-frontmatter",
            skill_md="# No frontmatter\n",
            metadata_json='{"version": "1.0.0"}',
        )

        exit_code = validate_skills.validate_skills(self.root)
        self.assertEqual(exit_code, 1)

    def test_validate_skills_fails_without_required_frontmatter_keys(self):
        self._create_skill(
            name="missing-description",
            skill_md=(
                "---\n"
                "name: missing-description\n"
                "---\n\n"
                "# Missing Description\n"
            ),
            metadata_json='{"version": "1.0.0"}',
        )

        exit_code = validate_skills.validate_skills(self.root)
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
