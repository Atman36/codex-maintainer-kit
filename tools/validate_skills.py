#!/usr/bin/env python3
"""
validate_skills.py - Validates integrity of local skill packages.

Checks:
1. `SKILL.md` exists.
2. `SKILL.md` includes frontmatter with required keys: `name`, `description`.
3. `metadata.json` exists, is valid JSON, and contains a `version` field.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from contract_registry import collect_contract_issues  # noqa: E402

FRONTMATTER_REQUIRED_KEYS = ("name", "description")
FRONTMATTER_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*\s*:")


@dataclass
class SkillCheckResult:
    skill_name: str
    errors: list[str]


def _extract_frontmatter_keys(skill_md_path: Path) -> set[str]:
    content = skill_md_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return set()

    keys: set[str] = set()
    for line in lines[1:]:
        if line.strip() == "---":
            return keys
        # Capture only top-level keys in frontmatter.
        if line.startswith((" ", "\t")):
            continue
        if FRONTMATTER_KEY_PATTERN.match(line):
            key = line.split(":", 1)[0].strip()
            keys.add(key)

    # No closing `---` found.
    return set()


def _validate_skill_dir(skill_dir: Path) -> SkillCheckResult:
    errors: list[str] = []
    skill_name = skill_dir.name

    skill_md_path = skill_dir / "SKILL.md"
    if not skill_md_path.exists():
        errors.append("Missing SKILL.md")
    else:
        frontmatter_keys = _extract_frontmatter_keys(skill_md_path)
        if not frontmatter_keys:
            errors.append("Missing or invalid YAML frontmatter in SKILL.md")
        else:
            missing_keys = [
                key for key in FRONTMATTER_REQUIRED_KEYS if key not in frontmatter_keys
            ]
            if missing_keys:
                errors.append(
                    "SKILL.md frontmatter missing required key(s): "
                    + ", ".join(missing_keys)
                )

    metadata_path = skill_dir / "metadata.json"
    if not metadata_path.exists():
        errors.append("Missing metadata.json")
    else:
        try:
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                errors.append("metadata.json must be a JSON object")
            elif "version" not in data:
                errors.append("metadata.json missing required key: version")
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid JSON in metadata.json: {exc}")
        except OSError as exc:
            errors.append(f"Error reading metadata.json: {exc}")

    return SkillCheckResult(skill_name=skill_name, errors=errors)


def validate_skills(root_dir: Path) -> int:
    skills_dir = root_dir / "skills"
    if not skills_dir.exists():
        print(f"Error: skills directory not found at {skills_dir}")
        return 1

    skill_dirs = sorted(
        (
            item
            for item in skills_dir.iterdir()
            if item.is_dir() and not item.name.startswith((".", "__"))
        ),
        key=lambda path: path.name,
    )

    print(f"Scanning skills in {skills_dir}...")
    results = [_validate_skill_dir(skill_dir) for skill_dir in skill_dirs]
    contract_issues = collect_contract_issues(root_dir)
    contract_errors = [issue for issue in contract_issues if issue.severity == "error"]
    contract_warnings = [issue for issue in contract_issues if issue.severity == "warning"]

    errors = [result for result in results if result.errors]
    if contract_warnings:
        print("\nContract warnings:")
        for issue in contract_warnings:
            print(f" - [{issue.path.relative_to(root_dir)}] {issue.message}")

    if errors or contract_errors:
        print("\nValidation failed:")
        for result in errors:
            for error in result.errors:
                print(f" - [{result.skill_name}] {error}")
        for issue in contract_errors:
            print(f" - [{issue.path.relative_to(root_dir)}] {issue.message}")
        return 1

    print(f"\nAll {len(results)} skills validated successfully.")
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate local skill packages.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repository root containing the skills/ directory",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    return validate_skills(args.root.resolve())


if __name__ == "__main__":
    sys.exit(main())
