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
    "CLAUDE.md",
    "skills/README.md",
    "skills/WORKFLOW.md",
    "tools/README.md",
)

SKILL_TEXT_PATTERNS = (
    "SKILL.md",
    "README.md",
    "AGENTS.md",
    "WORKFLOW.md",
    "references/**/*.md",
    "examples/**/*.md",
)

STALE_TEXT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\bCANDIDATES_JSON\b"),
        "Deprecated alias 'CANDIDATES_JSON' is stale guidance in docs/examples. Use canonical candidate inputs (`SCOUT_JSON`, `ANALYST_JSON`, or `ARCHITECT_JSON`) instead.",
    ),
    (
        re.compile(r"\bIMPLEMENT_RESULT_JSON\b"),
        "Deprecated alias 'IMPLEMENT_RESULT_JSON' is stale guidance in docs/examples. Use canonical `IMPLEMENT_JSON` instead.",
    ),
    (
        re.compile(r"\bpr_spec\.files_touched\b"),
        "Stale field path 'pr_spec.files_touched' found in docs/examples. Refer to the PRSpec `files_touched` field instead.",
    ),
    (
        re.compile(r"\bpytest\s+tools/tests/"),
        "Stale test command found in docs/examples. Use the unittest-based commands from `.github/workflows/test.yml` instead.",
    ),
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


def validate_stale_text_patterns(path: Path, text: str) -> list[ContractIssue]:
    issues: list[ContractIssue] = []
    for pattern, message in STALE_TEXT_PATTERNS:
        if pattern.search(text):
            issues.append(
                ContractIssue(
                    severity="error",
                    path=path,
                    message=message,
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


def iter_contract_text_files(root_dir: Path) -> list[Path]:
    files: set[Path] = set()

    prompts_dir = root_dir / "prompts"
    if prompts_dir.exists():
        files.update(prompt_path for prompt_path in prompts_dir.glob("*.md") if prompt_path.is_file())

    for doc_rel_path in DOC_FILES:
        doc_path = root_dir / doc_rel_path
        if doc_path.exists() and doc_path.is_file():
            files.add(doc_path)

    skills_dir = root_dir / "skills"
    if skills_dir.exists():
        for skill_dir in sorted(skills_dir.glob("pr-factory-*")):
            for pattern in SKILL_TEXT_PATTERNS:
                files.update(path for path in skill_dir.glob(pattern) if path.is_file())

    return sorted(files)


def _is_prompt_file(root_dir: Path, path: Path) -> bool:
    prompts_dir = root_dir / "prompts"
    return prompts_dir in path.parents


def collect_contract_issues(root_dir: Path) -> list[ContractIssue]:
    issues: list[ContractIssue] = []
    for text_path in iter_contract_text_files(root_dir):
        text = text_path.read_text(encoding="utf-8")
        issues.extend(validate_placeholder_text(text_path, text))
        if not _is_prompt_file(root_dir, text_path):
            issues.extend(validate_stale_text_patterns(text_path, text))

    skills_dir = root_dir / "skills"
    if skills_dir.exists():
        for skill_dir in sorted(skills_dir.glob("pr-factory-*")):
            metadata_path = skill_dir / "metadata.json"
            if metadata_path.exists():
                try:
                    metadata_payload = json.loads(metadata_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                issues.extend(validate_metadata_contracts(metadata_path, metadata_payload))

    return sorted(issues, key=lambda item: (str(item.path), item.severity, item.message))
