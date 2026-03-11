from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PLACEHOLDER_PATTERN = re.compile(r"\{\{([A-Z0-9_]+)\}\}")

CANONICAL_PLACEHOLDERS: dict[str, str] = {
    "ALLOWED_COMMANDS": "Optional allowlist of commands for implementation/verification.",
    "ALLOWED_FILES_HINT": "Optional file-scope hint for critic evaluation.",
    "ANALYST_JSON": "Path to Analyst ExecutionResult JSON saved by runtime.",
    "ARTIFACT_DIR": "Directory where analysis-stage JSON artifacts should be written.",
    "ARCHITECT_JSON": "Path to Architect ExecutionResult JSON saved by runtime.",
    "BASE_BRANCH": "Base branch name.",
    "CHANGE_REQUEST": "Direct change request for targeted code edits.",
    "COMMAND": "Expanded stage command for task runner wrappers.",
    "CONSTRAINTS": "Additional constraints passed into a stage or direct edit task.",
    "CONTEXT_PATH": "Optional external context path.",
    "CRITIC_JSON": "Path to Critic ExecutionResult JSON saved by runtime.",
    "DIFF_SUMMARY": "Optional diff summary string.",
    "FILE_HINTS": "Optional list of likely files to inspect/edit.",
    "FOCUS": "Analysis focus.",
    "GATEKEEPER_JSON": "Path to Gatekeeper ExecutionResult JSON saved by runtime.",
    "HEAD_BRANCH": "Normalized head branch name.",
    "IMPLEMENT_JSON": "Path to Implementer ExecutionResult JSON saved by runtime.",
    "MAX_PRS": "Maximum PR count to keep/select.",
    "MODE": "Pipeline mode.",
    "POLICY_BRIEF": "Optional policy brief for critic.",
    "PRSPEC_JSON": "Path to PRSpec JSON file.",
    "PROPOSED_CHANGES": "Candidate ideas or PRSpecs under review.",
    "PR_INDEX": "1-based index of the current PR iteration.",
    "RELATED_FILES": "Optional scoped file list for implementation.",
    "REPORT_PATH": "Path where a markdown report should be written.",
    "REPO_ROOT": "Repository root path.",
    "REPO_URL": "Repository URL.",
    "REVIEWER_JSON": "Path to Reviewer ExecutionResult JSON saved by runtime.",
    "RISK_BUDGET": "Optional risk budget for critic.",
    "RUNNER": "Optional runner selection for pipeline skill usage.",
    "SCOUT_JSON": "Path to Scout ExecutionResult JSON saved by runtime.",
    "STAGE": "Current stage name for task runner wrappers.",
    "TEMP_DIR": "Temporary working directory created by runtime.",
    "TIME_BUDGET": "Optional time budget for critic.",
    "VERIFY_COMMANDS": "Explicit verification commands for direct edit tasks.",
}

PLACEHOLDER_ALIASES: dict[str, tuple[str, ...]] = {
    "CANDIDATES_JSON": ("ANALYST_JSON", "ARCHITECT_JSON", "SCOUT_JSON"),
    "IMPLEMENT_RESULT_JSON": ("IMPLEMENT_JSON",),
}

DOC_FILES = (
    "README.md",
    "AGENTS.md",
    "skills/README.md",
    "tools/README.md",
)


@dataclass(frozen=True)
class ContractIssue:
    severity: str
    path: Path
    message: str


def extract_placeholders(text: str) -> set[str]:
    return {match.group(1) for match in PLACEHOLDER_PATTERN.finditer(text)}


def _alias_message(name: str) -> str:
    canonical_names = ", ".join(PLACEHOLDER_ALIASES[name])
    return (
        f"Placeholder '{name}' is a legacy alias. Prefer canonical placeholder(s): "
        f"{canonical_names}."
    )


def validate_placeholder_text(path: Path, text: str) -> list[ContractIssue]:
    issues: list[ContractIssue] = []
    for placeholder in sorted(extract_placeholders(text)):
        if placeholder in PLACEHOLDER_ALIASES:
            issues.append(
                ContractIssue(
                    severity="warning",
                    path=path,
                    message=_alias_message(placeholder),
                )
            )
            continue
        if placeholder not in CANONICAL_PLACEHOLDERS:
            issues.append(
                ContractIssue(
                    severity="error",
                    path=path,
                    message=f"Unknown placeholder '{placeholder}'. Add it to tools/contract_registry.py or fix the reference.",
                )
            )
    return issues


def validate_metadata_contracts(path: Path, payload: Any) -> list[ContractIssue]:
    if not isinstance(payload, dict):
        return []

    issues: list[ContractIssue] = []
    inputs = payload.get("inputs")
    if not isinstance(inputs, list):
        return issues

    for entry in inputs:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            continue

        if name in PLACEHOLDER_ALIASES:
            issues.append(
                ContractIssue(
                    severity="warning",
                    path=path,
                    message=_alias_message(name),
                )
            )
        elif name not in CANONICAL_PLACEHOLDERS:
            issues.append(
                ContractIssue(
                    severity="error",
                    path=path,
                    message=f"Unknown metadata input '{name}'. Add it to tools/contract_registry.py or fix metadata.json.",
                )
            )

        if name.endswith("_JSON") and entry.get("type") != "string":
            issues.append(
                ContractIssue(
                    severity="error",
                    path=path,
                    message=(
                        f"Metadata input '{name}' must use type 'string': runtime passes JSON file paths, "
                        f"not in-memory objects."
                    ),
                )
            )

    return issues


def collect_contract_issues(root_dir: Path) -> list[ContractIssue]:
    issues: list[ContractIssue] = []

    prompts_dir = root_dir / "prompts"
    if prompts_dir.exists():
        for prompt_path in sorted(prompts_dir.glob("*.md")):
            issues.extend(
                validate_placeholder_text(
                    prompt_path,
                    prompt_path.read_text(encoding="utf-8"),
                )
            )

    skills_dir = root_dir / "skills"
    if skills_dir.exists():
        for skill_dir in sorted(skills_dir.glob("pr-factory-*")):
            skill_md_path = skill_dir / "SKILL.md"
            if skill_md_path.exists():
                issues.extend(
                    validate_placeholder_text(
                        skill_md_path,
                        skill_md_path.read_text(encoding="utf-8"),
                    )
                )

            metadata_path = skill_dir / "metadata.json"
            if metadata_path.exists():
                try:
                    metadata_payload = json.loads(metadata_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                issues.extend(validate_metadata_contracts(metadata_path, metadata_payload))

    for doc_rel_path in DOC_FILES:
        doc_path = root_dir / doc_rel_path
        if not doc_path.exists():
            continue
        issues.extend(
            validate_placeholder_text(
                doc_path,
                doc_path.read_text(encoding="utf-8"),
            )
        )

    return sorted(issues, key=lambda item: (str(item.path), item.severity, item.message))
