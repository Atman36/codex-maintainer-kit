#!/usr/bin/env python3
"""
Deterministic PR Factory orchestrator.

This runner executes analysis stages once, then runs implementation stages per PRSpec.
It supports preflight checks, runner adapters, multi-PR loops, publish readiness,
and machine-readable summary artifacts.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

# Ensure `tools/` is on sys.path so this script works both as:
# - `python tools/run_pipeline.py ...`
# - imported via tests using importlib.spec_from_file_location(...)
TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from pr_factory_lib.git_utils import run_git  # noqa: E402
from pr_factory_lib.json_utils import parse_stage_output, write_json  # noqa: E402
from pr_factory_lib.schema_utils import SchemaValidationError, validate_pipeline_summary, validate_stage_payload  # noqa: E402


IMPLEMENTATION_STAGES: List[str] = ["implement", "reviewer", "pr_writer"]
DEFAULT_PIPELINE_MODES_CONFIG_PATH = TOOLS_DIR.parent / "config" / "pipeline_modes.json"
REQUIRED_PIPELINE_MODES: Tuple[str, ...] = ("full", "quick-win", "architecture")
ALLOWED_ANALYSIS_STAGES = frozenset({"scout", "analyst", "architect", "critic", "gatekeeper"})
STOP_AFTER_STAGES: Tuple[str, ...] = (
    "scout",
    "analyst",
    "architect",
    "critic",
    "gatekeeper",
    "implement",
    "reviewer",
    "pr_writer",
    "publish",
)
PLACEHOLDER_ALIAS_PREFERENCES: Dict[str, Tuple[str, ...]] = {
    "CANDIDATES_JSON": ("ANALYST_JSON", "ARCHITECT_JSON", "SCOUT_JSON"),
    "IMPLEMENT_RESULT_JSON": ("IMPLEMENT_JSON",),
}
UNRESOLVED_PLACEHOLDER_RX = re.compile(r"\{\{([^{}]+)\}\}")


class PipelineModeConfigError(ValueError):
    pass


@dataclass
class StageRun:
    stage: str
    command: str
    exit_code: int
    stdout: str
    stderr: str
    payload: Optional[Dict[str, Any]]
    elapsed_ms: int
    runner: str


@dataclass
class StructuredError:
    reason: str
    failed_stage: str
    next_action: str

    def as_dict(self) -> Dict[str, str]:
        return {
            "reason": self.reason,
            "failed_stage": self.failed_stage,
            "next_action": self.next_action,
        }

    def as_text(self) -> str:
        return f"[{self.failed_stage}] {self.reason} | next_action: {self.next_action}"


@dataclass
class PreflightCheck:
    name: str
    status: str
    detail: str
    next_action: str = ""


@dataclass
class PreflightResult:
    passed: bool
    checks: List[PreflightCheck]
    errors: List[StructuredError]
    warnings: List[str]
    base_sha_at_start: str
    runner_selected: str


class RunnerAdapter:
    name = "base"

    def is_available(self, cwd: Path) -> Tuple[bool, str]:
        raise NotImplementedError

    def build_command(self, stage: str, expanded_command: str) -> str:
        raise NotImplementedError


class CliRunnerAdapter(RunnerAdapter):
    name = "cli"

    def is_available(self, cwd: Path) -> Tuple[bool, str]:
        return True, "cli runner available"

    def build_command(self, stage: str, expanded_command: str) -> str:
        return expanded_command


class TaskRunnerAdapter(RunnerAdapter):
    name = "task"

    def __init__(self, wrapper: str) -> None:
        self.wrapper = wrapper.strip()

    def is_available(self, cwd: Path) -> Tuple[bool, str]:
        if not self.wrapper:
            return False, "task runner wrapper is not configured"
        try:
            parts = shlex.split(self.wrapper)
        except ValueError as exc:
            return False, f"invalid task wrapper: {exc}"
        if not parts:
            return False, "task runner wrapper is empty"
        binary = parts[0]
        if shutil.which(binary) is None:
            return False, f"task runner binary not found: {binary}"
        return True, f"task runner available via wrapper '{self.wrapper}'"

    def build_command(self, stage: str, expanded_command: str) -> str:
        if "{{COMMAND}}" in self.wrapper:
            cmd = self.wrapper.replace("{{COMMAND}}", shlex.quote(expanded_command))
        else:
            cmd = f"{self.wrapper} {shlex.quote(expanded_command)}"
        return cmd.replace("{{STAGE}}", stage)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def new_run_id() -> str:
    return str(uuid.uuid4())


def pipeline_id_for_run(run_id: str) -> str:
    return f"pipeline-{run_id}"


def run_artifact_dir(repo_root: Path, run_id: str) -> Path:
    return default_artifact_dir(repo_root) / "runs" / run_id


def default_report_path(repo_root: Path, run_id: str) -> Path:
    return run_artifact_dir(repo_root, run_id) / "report.md"


def default_analysis_artifact_dir(repo_root: Path, run_id: str) -> Path:
    return run_artifact_dir(repo_root, run_id) / "analysis"


def default_pr_artifact_dir(repo_root: Path, run_id: str, pr_index: int) -> Path:
    return run_artifact_dir(repo_root, run_id) / "prs" / f"pr-{pr_index}"


@lru_cache(maxsize=None)
def _load_pipeline_mode_analysis_stage_order(config_path_str: str) -> Dict[str, List[str]]:
    config_path = Path(config_path_str)
    if not config_path.exists():
        raise PipelineModeConfigError(f"Pipeline mode config is missing: {config_path}")

    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PipelineModeConfigError(f"Pipeline mode config is not valid JSON: {config_path} ({exc})") from exc

    if not isinstance(payload, dict):
        raise PipelineModeConfigError(f"Pipeline mode config must be a JSON object: {config_path}")

    analysis_stage_order = payload.get("analysis_stage_order")
    if not isinstance(analysis_stage_order, dict):
        raise PipelineModeConfigError(
            f"Pipeline mode config must define object field 'analysis_stage_order': {config_path}"
        )

    loaded: Dict[str, List[str]] = {}
    for mode, stages in analysis_stage_order.items():
        if not isinstance(mode, str) or not mode.strip():
            raise PipelineModeConfigError(
                f"Pipeline mode config contains an empty mode name in 'analysis_stage_order': {config_path}"
            )
        if not isinstance(stages, list) or not stages or not all(isinstance(stage, str) and stage.strip() for stage in stages):
            raise PipelineModeConfigError(
                f"Pipeline mode config mode '{mode}' must be a non-empty array of stage names: {config_path}"
            )
        unknown_stages = sorted({stage for stage in stages if stage not in ALLOWED_ANALYSIS_STAGES})
        if unknown_stages:
            allowed_text = ", ".join(sorted(ALLOWED_ANALYSIS_STAGES))
            unknown_text = ", ".join(unknown_stages)
            raise PipelineModeConfigError(
                f"Pipeline mode config mode '{mode}' contains unknown stage(s): {unknown_text}. "
                f"Allowed analysis stages: {allowed_text}."
            )
        loaded[mode] = list(stages)

    missing_modes = [mode for mode in REQUIRED_PIPELINE_MODES if mode not in loaded]
    if missing_modes:
        raise PipelineModeConfigError(
            "Pipeline mode config is missing required mode(s): " + ", ".join(missing_modes)
        )
    return loaded


def load_pipeline_mode_analysis_stage_order(config_path: Optional[Path] = None) -> Dict[str, List[str]]:
    resolved_path = (config_path or DEFAULT_PIPELINE_MODES_CONFIG_PATH).resolve()
    return _load_pipeline_mode_analysis_stage_order(str(resolved_path))


def parse_stage_commands(items: List[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Invalid --stage-command '{item}'. Expected <stage>=<command>.")
        stage, cmd = item.split("=", 1)
        stage = stage.strip()
        cmd = cmd.strip()
        if not stage or not cmd:
            raise ValueError(f"Invalid --stage-command '{item}'. Stage and command must be non-empty.")
        out[stage] = cmd
    return out


def expand_template(template: str, values: Dict[str, str]) -> str:
    resolved_values = dict(values)
    for alias, candidates in PLACEHOLDER_ALIAS_PREFERENCES.items():
        for candidate in candidates:
            candidate_value = resolved_values.get(candidate, "")
            if candidate_value:
                resolved_values[alias] = candidate_value
                break

    out = template
    for k, v in resolved_values.items():
        out = out.replace("{{" + k + "}}", v)

    unresolved = sorted({match.group(1).strip() for match in UNRESOLVED_PLACEHOLDER_RX.finditer(out)})
    if unresolved:
        unresolved_text = ", ".join(f"{{{{{name}}}}}" for name in unresolved)
        raise ValueError(f"Unresolved placeholder(s) in stage command: {unresolved_text}")
    return out


def run_process(command: str, cwd: Path, env: Dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        shell=True,
        capture_output=True,
        text=True,
    )


def run_stage(
    adapter: RunnerAdapter,
    stage: str,
    command_template: str,
    cwd: Path,
    template_values: Dict[str, str],
    extra_env: Optional[Dict[str, str]] = None,
) -> StageRun:
    expanded = expand_template(command_template, template_values)
    command = adapter.build_command(stage=stage, expanded_command=expanded)

    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    started = time.time()
    proc = run_process(command=command, cwd=cwd, env=env)
    elapsed_ms = int((time.time() - started) * 1000)

    payload: Optional[Dict[str, Any]] = None
    if proc.returncode == 0:
        payload = parse_stage_output(proc.stdout)
        validate_stage_payload(payload=payload, expected_stage=stage)
    return StageRun(
        stage=stage,
        command=command,
        exit_code=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        payload=payload,
        elapsed_ms=elapsed_ms,
        runner=adapter.name,
    )


def resolve_base_sha(
    repo_root: Path,
    base_branch: str,
    allow_local_fallback: bool = False,
) -> Tuple[str, str]:
    refs = [f"origin/{base_branch}"]
    if allow_local_fallback:
        refs.extend([base_branch, "HEAD"])
    for ref in refs:
        proc = run_git(["rev-parse", "--verify", ref], cwd=repo_root)
        if proc.returncode == 0:
            return proc.stdout.strip(), ref
    if allow_local_fallback:
        raise ValueError(
            f"Cannot resolve base SHA for '{base_branch}'. Tried origin/{base_branch}, local {base_branch}, and HEAD."
        )
    raise ValueError(f"Cannot resolve base SHA for '{base_branch}'. Missing origin/{base_branch}.")


def stage_status(payload: Dict[str, Any]) -> str:
    return str(payload.get("status", "")).strip().lower()


def critic_decision(payload: Dict[str, Any]) -> str:
    data = payload.get("data")
    if isinstance(data, dict):
        decision = data.get("decision")
        if isinstance(decision, str):
            return decision.strip().lower()

    # Backward-compat: older Critic payloads used top-level "decision".
    return str(payload.get("decision", "")).strip().lower()


def gatekeeper_decision(payload: Dict[str, Any]) -> str:
    data = payload.get("data", {})
    if isinstance(data, dict):
        pr_specs = data.get("pr_specs")
        if isinstance(pr_specs, list) and any(isinstance(item, dict) for item in pr_specs):
            return "pr"

        selected = data.get("selected")
        if isinstance(selected, list):
            decisions: List[str] = []
            for item in selected:
                if isinstance(item, dict):
                    decision = str(item.get("decision", "")).strip().lower()
                    if decision:
                        decisions.append(decision)
                    if isinstance(item.get("pr_spec"), dict):
                        return "pr"
            if "pr" in decisions:
                return "pr"
            if decisions:
                return decisions[0]

    pr_specs_top = payload.get("pr_specs")
    if isinstance(pr_specs_top, list) and any(isinstance(item, dict) for item in pr_specs_top):
        return "pr"

    if isinstance(payload.get("pr_spec"), dict) and payload["pr_spec"]:
        return "pr"
    return ""


def gate_failed(stage: str, payload: Dict[str, Any]) -> Optional[str]:
    if stage == "critic":
        decision = critic_decision(payload)
        if decision != "approve":
            return f"Critic gate failed: decision={decision or 'missing'}"
    elif stage == "gatekeeper":
        decision = gatekeeper_decision(payload)
        status = stage_status(payload)
        if decision != "pr":
            return f"Gatekeeper gate failed: decision={decision or 'missing'}"
        if status != "success":
            return f"Gatekeeper gate failed: status={status or 'missing'}"
    elif stage in ("implement", "reviewer", "pr_writer", "publish"):
        status = stage_status(payload)
        if status != "success":
            return f"{stage} gate failed: status={status or 'missing'}"
    return None


def collect_top_improvements(stage_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = stage_payload.get("data", {})
    if isinstance(data, dict):
        candidates = data.get("candidates")
        if isinstance(candidates, list):
            normalized_candidates = [c for c in candidates if isinstance(c, dict)]
            if normalized_candidates:
                return normalized_candidates
        candidate = data.get("candidate")
        if isinstance(candidate, dict):
            return [candidate]
    return []


def looks_like_skill_name(command: str) -> bool:
    stripped = command.strip()
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9\-]*", stripped)) and stripped.startswith("pr-factory-")


def ensure_command_available(binary: str) -> bool:
    return shutil.which(binary) is not None


def detect_command_binary(command: str) -> Optional[str]:
    try:
        parts = shlex.split(command)
    except ValueError:
        return None
    if not parts:
        return None

    index = 0
    env_assign = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=.*$")
    while index < len(parts) and env_assign.match(parts[index]):
        index += 1
    if index >= len(parts):
        return None

    token = parts[index]
    if token.startswith("{{") and token.endswith("}}"):
        return None
    return token


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-._").lower()
    slug = re.sub(r"-{2,}", "-", slug)
    return slug


def default_artifact_dir(repo_root: Path) -> Path:
    return repo_root / "analysis_report"


def persist_stage_payload(
    payload: Dict[str, Any],
    *,
    path: Path,
    run_id: str,
    artifact_root: Path,
    lineage: Dict[str, Any],
) -> Dict[str, Any]:
    persisted_payload = json.loads(json.dumps(payload))
    data = persisted_payload.get("data")
    if not isinstance(data, dict):
        data = {}
        persisted_payload["data"] = data

    payload_lineage = data.get("lineage")
    if not isinstance(payload_lineage, dict):
        payload_lineage = {}

    payload_lineage.update(lineage)
    payload_lineage["artifact_root"] = str(artifact_root)
    payload_lineage["stage_payload_path"] = str(path)
    data["lineage"] = payload_lineage
    data["run_id"] = run_id

    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, persisted_payload)
    return persisted_payload


def normalize_head_branch(pr_spec: Dict[str, Any], index: int) -> str:
    title = str(pr_spec.get("title") or "").strip()
    source_branch = ""
    head = pr_spec.get("head")
    if isinstance(head, dict):
        source_branch = str(head.get("branch") or "").strip()
    if ":" in source_branch:
        source_branch = source_branch.split(":", 1)[1]

    base_slug = slugify(source_branch or title or f"pr-{index}")
    if not base_slug:
        base_slug = f"pr-{index}"
    if base_slug.startswith("codex/"):
        branch = base_slug
    elif source_branch.startswith("codex/"):
        branch = f"codex/{slugify(source_branch[6:]) or f'pr-{index}'}"
    else:
        branch = f"codex/{base_slug}"
    return branch[:80]


def normalize_pr_spec(
    raw_pr_spec: Dict[str, Any],
    index: int,
    base_branch: str,
    repo_url: str,
) -> Dict[str, Any]:
    pr_spec = json.loads(json.dumps(raw_pr_spec))
    if not isinstance(pr_spec, dict):
        return {}

    pr_spec.setdefault("schema_version", "1.0")
    pr_spec.setdefault("id", f"prspec-{index}")

    repo = pr_spec.get("repo")
    if not isinstance(repo, dict):
        repo = {}
        pr_spec["repo"] = repo
    if repo_url and not repo.get("url"):
        repo["url"] = repo_url
    if not repo.get("default_branch"):
        repo["default_branch"] = base_branch

    base = pr_spec.get("base")
    if not isinstance(base, dict):
        base = {}
        pr_spec["base"] = base
    if not base.get("branch"):
        base["branch"] = base_branch

    head = pr_spec.get("head")
    if not isinstance(head, dict):
        head = {}
        pr_spec["head"] = head
    head["branch"] = normalize_head_branch(pr_spec, index)

    return pr_spec


def extract_pr_specs(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []

    data = payload.get("data")
    if isinstance(data, dict):
        direct = data.get("pr_specs")
        if isinstance(direct, list):
            found.extend([item for item in direct if isinstance(item, dict)])

        selected = data.get("selected")
        if isinstance(selected, list):
            for item in selected:
                if isinstance(item, dict) and isinstance(item.get("pr_spec"), dict):
                    found.append(item["pr_spec"])

    top = payload.get("pr_specs")
    if isinstance(top, list):
        found.extend([item for item in top if isinstance(item, dict)])

    pr_spec = payload.get("pr_spec")
    if isinstance(pr_spec, dict) and pr_spec:
        found.append(pr_spec)

    unique: List[Dict[str, Any]] = []
    seen_keys = set()
    for spec in found:
        key = str(spec.get("id") or json.dumps(spec, sort_keys=True, ensure_ascii=False))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        unique.append(spec)
    return unique


def select_runner(mode: str, task_runner_cmd: str, cwd: Path) -> Tuple[RunnerAdapter, List[str]]:
    adapters: Dict[str, RunnerAdapter] = {
        "task": TaskRunnerAdapter(task_runner_cmd),
        "cli": CliRunnerAdapter(),
    }

    warnings: List[str] = []
    if mode in {"task", "cli"}:
        adapter = adapters[mode]
        ok, reason = adapter.is_available(cwd)
        if not ok:
            raise ValueError(f"Requested runner '{mode}' is not available: {reason}")
        return adapter, warnings

    for candidate in ["task", "cli"]:
        adapter = adapters[candidate]
        ok, reason = adapter.is_available(cwd)
        if ok:
            if candidate != "task":
                warnings.append("Runner auto fallback: task unavailable, selected cli")
            return adapter, warnings
        warnings.append(f"Runner candidate '{candidate}' unavailable: {reason}")

    raise ValueError("No runner backend is available")


def run_preflight(
    repo_root: Path,
    base_branch: str,
    allow_dirty: bool,
    publish_requested: bool,
    stage_commands: Dict[str, str],
    required_stages: List[str],
    runner_selected: str,
    command_exists_fn: Callable[[str], bool] = ensure_command_available,
) -> PreflightResult:
    checks: List[PreflightCheck] = []
    errors: List[StructuredError] = []
    warnings: List[str] = []
    base_sha_at_start = ""

    def fail(name: str, detail: str, next_action: str) -> None:
        checks.append(PreflightCheck(name=name, status="failed", detail=detail, next_action=next_action))
        errors.append(StructuredError(reason=detail, failed_stage="preflight", next_action=next_action))

    def ok(name: str, detail: str) -> None:
        checks.append(PreflightCheck(name=name, status="ok", detail=detail))

    if not repo_root.exists() or not repo_root.is_dir():
        fail(
            "repo_root",
            f"Repository root not found: {repo_root}",
            "Provide an existing --repo-root path and rerun.",
        )
        return PreflightResult(False, checks, errors, warnings, base_sha_at_start, runner_selected)
    ok("repo_root", f"Found repository root: {repo_root}")

    git_probe = run_git(["rev-parse", "--is-inside-work-tree"], cwd=repo_root)
    if git_probe.returncode != 0:
        fail(
            "git_repo",
            "Target path is not a git repository.",
            "Run inside a git repository or initialize one with `git init`.",
        )
        return PreflightResult(False, checks, errors, warnings, base_sha_at_start, runner_selected)
    ok("git_repo", "Git repository detected")

    if not allow_dirty:
        dirty = run_git(["status", "--porcelain"], cwd=repo_root)
        if dirty.returncode != 0:
            fail(
                "dirty_worktree",
                "Failed to inspect git worktree status.",
                "Run `git status` manually and fix repository state.",
            )
            return PreflightResult(False, checks, errors, warnings, base_sha_at_start, runner_selected)
        if dirty.stdout.strip():
            fail(
                "dirty_worktree",
                "Working tree is dirty but pipeline requires clean state.",
                "Commit/stash changes or rerun with --allow-dirty if intentional.",
            )
            return PreflightResult(False, checks, errors, warnings, base_sha_at_start, runner_selected)
    ok("dirty_worktree", "Worktree policy satisfied")

    origin = run_git(["remote", "get-url", "origin"], cwd=repo_root)
    has_origin = origin.returncode == 0
    if publish_requested:
        if not has_origin:
            fail(
                "remotes",
                "Missing required remote 'origin'.",
                "Add upstream remote: `git remote add origin <url>`.",
            )
            return PreflightResult(False, checks, errors, warnings, base_sha_at_start, runner_selected)
        ok("remotes", f"origin={origin.stdout.strip()}")
    elif has_origin:
        ok("remotes", f"origin={origin.stdout.strip()}")
    else:
        warning = (
            "Missing remote 'origin'; continuing with local-only preflight because publish mode is not requested."
        )
        warnings.append(warning)
        checks.append(
            PreflightCheck(
                name="remotes",
                status="warn",
                detail=warning,
                next_action="Add `origin` before using --publish.",
            )
        )

    try:
        base_sha_at_start, base_ref_used = resolve_base_sha(
            repo_root=repo_root,
            base_branch=base_branch,
            allow_local_fallback=not publish_requested,
        )
        detail = f"base_sha_at_start={base_sha_at_start} ({base_ref_used})"
        if publish_requested or base_ref_used == f"origin/{base_branch}":
            ok("base_sha", detail)
        else:
            if base_ref_used == base_branch:
                warning = (
                    f"Preflight used local base branch '{base_branch}' because origin/{base_branch} was unavailable. "
                    "Publish mode still requires the remote base."
                )
            else:
                warning = (
                    f"Preflight used HEAD because neither origin/{base_branch} nor local '{base_branch}' was "
                    "available. Publish mode still requires the remote base."
                )
            warnings.append(warning)
            checks.append(
                PreflightCheck(
                    name="base_sha",
                    status="warn",
                    detail=detail,
                    next_action=f"Fetch or add origin/{base_branch} before using --publish.",
                )
            )
    except ValueError as exc:
        next_action = f"Run `git fetch origin {base_branch}` and ensure the branch exists."
        if not publish_requested:
            next_action = (
                f"Create or check out a local '{base_branch}' branch, or ensure HEAD resolves to a commit, then rerun."
            )
        fail(
            "base_sha",
            str(exc),
            next_action,
        )
        return PreflightResult(False, checks, errors, warnings, base_sha_at_start, runner_selected)

    missing_stage_commands = [stage for stage in required_stages if stage not in stage_commands]
    if missing_stage_commands:
        fail(
            "stage_commands",
            f"Missing stage command(s): {', '.join(missing_stage_commands)}",
            "Provide each missing stage via --stage-command <stage>=<command>.",
        )
        return PreflightResult(False, checks, errors, warnings, base_sha_at_start, runner_selected)
    ok("stage_commands", "All required stage commands are provided")

    bad_skill_commands = [
        f"{stage}={cmd}" for stage, cmd in stage_commands.items() if looks_like_skill_name(cmd)
    ]
    if bad_skill_commands and runner_selected == "cli":
        fail(
            "skill_command_mode",
            "Detected skill names used as shell commands in CLI runner mode.",
            "Skills are instructions, not executables. Use real shell commands or configure --runner task.",
        )
        return PreflightResult(False, checks, errors, warnings, base_sha_at_start, runner_selected)
    ok("skill_command_mode", "Stage command format is compatible with selected runner")

    if runner_selected == "cli":
        missing_binaries: List[str] = []
        for stage in required_stages:
            cmd = stage_commands.get(stage, "")
            binary = detect_command_binary(cmd)
            if not binary:
                continue
            if binary.startswith(("/", "./", "../")):
                binary_path = Path(binary)
                if not binary_path.is_absolute():
                    binary_path = (repo_root / binary).resolve()
                if binary_path.exists():
                    continue
                missing_binaries.append(f"{stage}:{binary}")
                continue
            if not command_exists_fn(binary):
                missing_binaries.append(f"{stage}:{binary}")

        if missing_binaries:
            fail(
                "tooling",
                f"Missing required command binaries: {', '.join(missing_binaries)}",
                "Install missing tools or update --stage-command values to available executables.",
            )
            return PreflightResult(False, checks, errors, warnings, base_sha_at_start, runner_selected)
    ok("tooling", "Required command binaries look available")

    if publish_requested:
        if not command_exists_fn("gh"):
            fail(
                "publish_tooling",
                "GitHub CLI (gh) is required for publish mode but not found.",
                "Install gh and rerun. Example: https://cli.github.com/",
            )
            return PreflightResult(False, checks, errors, warnings, base_sha_at_start, runner_selected)

        gh_auth = subprocess.run(
            ["gh", "auth", "status"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        if gh_auth.returncode != 0:
            fail(
                "publish_auth",
                "GitHub auth is not ready (`gh auth status` failed).",
                "Authenticate with `gh auth login` and rerun.",
            )
            return PreflightResult(False, checks, errors, warnings, base_sha_at_start, runner_selected)
        ok("publish_auth", "GitHub auth is ready")

        fork_remote = run_git(["remote", "get-url", "fork"], cwd=repo_root)
        if fork_remote.returncode == 0:
            ok("fork_remote", f"fork={fork_remote.stdout.strip()}")
        else:
            warnings.append("No 'fork' remote found. Publisher is expected to create or configure it.")
            checks.append(
                PreflightCheck(
                    name="fork_remote",
                    status="warn",
                    detail="fork remote is missing",
                    next_action="Ensure publisher can create a fork or add `git remote add fork <url>`.",
                )
            )

    return PreflightResult(not errors, checks, errors, warnings, base_sha_at_start, runner_selected)


def execute_stage_with_retries(
    adapter: RunnerAdapter,
    stage: str,
    command_template: str,
    cwd: Path,
    template_values: Dict[str, str],
    max_attempts: int,
) -> Tuple[StageRun, int, List[Dict[str, Any]]]:
    attempt = 0
    last_error_text = ""
    retry_trace: List[Dict[str, Any]] = []
    final_run: Optional[StageRun] = None

    while attempt < max_attempts:
        attempt += 1
        extra_env = {
            "PR_FACTORY_STAGE": stage,
            "PR_FACTORY_ATTEMPT": str(attempt),
            "PR_FACTORY_MAX_ATTEMPTS": str(max_attempts),
            "PR_FACTORY_PREV_ERROR": last_error_text,
        }

        try:
            run_result = run_stage(
                adapter=adapter,
                stage=stage,
                command_template=command_template,
                cwd=cwd,
                template_values=template_values,
                extra_env=extra_env,
            )
        except (RuntimeError, ValueError) as exc:
            run_result = StageRun(
                stage=stage,
                command=command_template,
                exit_code=1,
                stdout="",
                stderr=str(exc),
                payload=None,
                elapsed_ms=0,
                runner=adapter.name,
            )

        final_run = run_result
        payload_status = ""
        if isinstance(run_result.payload, dict):
            payload_status = stage_status(run_result.payload)
        retry_trace.append(
            {
                "stage": stage,
                "attempt": attempt,
                "exit_code": run_result.exit_code,
                "payload_status": payload_status,
                "elapsed_ms": run_result.elapsed_ms,
                "stderr": (run_result.stderr or run_result.stdout).strip()[:500],
            }
        )

        if run_result.exit_code != 0:
            last_error_text = (run_result.stderr or run_result.stdout).strip()
            if stage == "implement" and attempt < max_attempts:
                continue
            break

        if stage == "implement" and isinstance(run_result.payload, dict):
            status = stage_status(run_result.payload)
            if status in {"retryable", "failed"} and attempt < max_attempts:
                last_error_text = str(run_result.payload.get("stderr", "") or run_result.stderr or "")
                continue
        break

    if final_run is None:
        raise RuntimeError("Internal error: stage did not execute")

    return final_run, attempt, retry_trace


def _build_pipeline_artifacts(summary_path: str = "", report_path: str = "") -> List[Dict[str, str]]:
    artifacts: List[Dict[str, str]] = []
    if summary_path:
        artifacts.append({"kind": "pipeline_summary", "path": summary_path})
    if report_path:
        report_candidate = Path(report_path)
        if report_candidate.exists():
            artifacts.append({"kind": "report", "path": str(report_candidate)})
    return artifacts


def make_failure_result(
    started_at: str,
    mode: str,
    run_id: str,
    stage_summaries: List[Dict[str, Any]],
    top_improvements: List[Dict[str, Any]],
    message: str,
    errors: List[str],
    warnings: List[str],
    error_blocks: List[StructuredError],
    runner_selected: str,
    preflight_checks: List[PreflightCheck],
    pr_results: Optional[List[Dict[str, Any]]] = None,
    summary_path: str = "",
    lineage: Optional[Dict[str, Any]] = None,
    final_pr_spec: Optional[Dict[str, Any]] = None,
    selected_pr_specs: Optional[List[Dict[str, Any]]] = None,
    report_path: str = "",
) -> Dict[str, Any]:
    pr_results = pr_results or []
    selected_pr_specs = selected_pr_specs or []
    first_pr_spec = final_pr_spec or {}
    if not first_pr_spec and selected_pr_specs:
        first_pr_spec = selected_pr_specs[0]
    pipeline_id = pipeline_id_for_run(run_id)
    lineage = lineage or {}

    final_pr_message: Dict[str, Any] = {}
    if isinstance(first_pr_spec, dict):
        title = first_pr_spec.get("title")
        body_markdown = first_pr_spec.get("body_markdown")
        if isinstance(title, str) and isinstance(body_markdown, str):
            final_pr_message = {"title": title, "body_markdown": body_markdown}

    return {
        "schema_version": "1.0",
        "id": pipeline_id,
        "stage": "pipeline",
        "status": "needs_human",
        "summary": message,
        "started_at": started_at,
        "finished_at": utc_now(),
        "exit_code": 1,
        "stdout": "",
        "stderr": "\n".join(errors),
        "artifacts": _build_pipeline_artifacts(summary_path=summary_path, report_path=report_path),
        "metrics": {
            "duration_ms": 0,
            "cost_usd": 0.0,
            "tokens_in": 0,
            "tokens_out": 0,
            "retries": 0,
        },
        "errors": errors,
        "warnings": warnings,
        "data": {
            "pipeline_mode": mode,
            "run_id": run_id,
            "runner_selected": runner_selected,
            "stage_summary": stage_summaries,
            "top_improvements": top_improvements,
            "selected_prspec": first_pr_spec if isinstance(first_pr_spec, dict) else {},
            "selected_prspecs": [
                item
                for item in (
                    [r.get("pr_spec", {}) for r in pr_results if isinstance(r, dict)]
                    or selected_pr_specs
                )
                if isinstance(item, dict)
            ],
            "final_pr_message": final_pr_message,
            "pr_results": pr_results,
            "report_path": report_path,
            "preflight": {
                "checks": [
                    {
                        "name": c.name,
                        "status": c.status,
                        "detail": c.detail,
                        "next_action": c.next_action,
                    }
                    for c in preflight_checks
                ]
            },
            "error_blocks": [e.as_dict() for e in error_blocks],
            "lineage": lineage,
            "pipeline_summary_path": summary_path,
        },
        "pr_spec": first_pr_spec if isinstance(first_pr_spec, dict) else {},
    }


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic PR Factory pipeline runner.")
    parser.add_argument("--repo-root", required=True, help="Absolute path to repository root.")
    parser.add_argument("--repo-url", default="", help="Repository URL.")
    parser.add_argument("--base-branch", default="main", help="Base branch.")
    parser.add_argument("--context-path", default="", help="Optional context path.")
    parser.add_argument("--focus", default="", help="Optional focus value for Analyst.")
    parser.add_argument("--mode", default="full", help="Pipeline mode defined in config/pipeline_modes.json.")
    parser.add_argument("--max-prs", type=int, default=1)
    parser.add_argument("--publish", action="store_true", help="Append publish stage.")
    parser.add_argument(
        "--implement-max-attempts",
        type=int,
        default=3,
        help="Max attempts for implement stage in retry loop.",
    )
    parser.add_argument(
        "--stage-command",
        action="append",
        default=[],
        metavar="STAGE=CMD",
        help="Command template for a stage. Use placeholders like {{REPO_ROOT}}.",
    )
    parser.add_argument(
        "--runner",
        choices=["auto", "task", "cli"],
        default="auto",
        help="Stage execution backend.",
    )
    parser.add_argument(
        "--task-runner-cmd",
        default=os.getenv("PR_FACTORY_TASK_RUNNER", ""),
        help="Task runner wrapper command (supports {{COMMAND}} and {{STAGE}} placeholders).",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow running pipeline with dirty git worktree.",
    )
    parser.add_argument(
        "--base-drift-policy",
        choices=["needs_human", "warn", "ignore"],
        default="needs_human",
        help="How to handle base branch drift before publish.",
    )
    parser.add_argument("--output", default="", help="Write final JSON to this file.")
    parser.add_argument(
        "--summary-output",
        default="",
        help="Write machine-readable pipeline summary JSON to this file.",
    )
    parser.add_argument(
        "--analysis-only",
        action="store_true",
        help="Run analysis stages only and stop after gatekeeper.",
    )
    parser.add_argument(
        "--stop-after",
        choices=STOP_AFTER_STAGES,
        default="",
        help="Stop the pipeline after the specified stage succeeds.",
    )
    return parser.parse_args(argv)


def _resolve_stop_after(args: argparse.Namespace) -> str:
    if args.analysis_only:
        if args.stop_after and args.stop_after != "gatekeeper":
            raise ValueError("--analysis-only is equivalent to --stop-after gatekeeper.")
        if args.publish:
            raise ValueError("--analysis-only cannot be combined with --publish.")
        return "gatekeeper"
    return args.stop_after.strip()


def _slice_required_stages(stage_order: List[str], stop_after_stage: str) -> List[str]:
    if not stop_after_stage:
        return list(stage_order)
    if stop_after_stage not in stage_order:
        return []
    stop_index = stage_order.index(stop_after_stage)
    return stage_order[: stop_index + 1]


def run_pipeline(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    started_at = utc_now()
    run_id = new_run_id()
    repo_root = Path(args.repo_root).resolve()

    try:
        stage_commands = parse_stage_commands(args.stage_command)
    except ValueError as exc:
        result = make_failure_result(
            started_at=started_at,
            mode=args.mode,
            run_id=run_id,
            stage_summaries=[],
            top_improvements=[],
            message=f"Invalid stage command: {exc}",
            errors=[str(exc)],
            warnings=[],
            error_blocks=[StructuredError(reason=str(exc), failed_stage="preflight", next_action="Fix --stage-command format and rerun.")],
            runner_selected="",
            preflight_checks=[],
        )
        return 1, result

    try:
        mode_analysis_stage_order = load_pipeline_mode_analysis_stage_order()
    except PipelineModeConfigError as exc:
        error = StructuredError(
            reason=str(exc),
            failed_stage="pipeline_mode_config",
            next_action="Restore/fix config/pipeline_modes.json and rerun.",
        )
        result = make_failure_result(
            started_at=started_at,
            mode=args.mode,
            run_id=run_id,
            stage_summaries=[],
            top_improvements=[],
            message="Pipeline mode config failed validation",
            errors=[error.as_text()],
            warnings=[],
            error_blocks=[error],
            runner_selected="",
            preflight_checks=[],
        )
        return 1, result

    if args.mode not in mode_analysis_stage_order:
        error = StructuredError(
            reason=f"Unknown pipeline mode '{args.mode}'. Available modes: {', '.join(sorted(mode_analysis_stage_order))}",
            failed_stage="pipeline_mode_config",
            next_action="Pick a configured mode or update config/pipeline_modes.json.",
        )
        result = make_failure_result(
            started_at=started_at,
            mode=args.mode,
            run_id=run_id,
            stage_summaries=[],
            top_improvements=[],
            message="Requested pipeline mode is not configured",
            errors=[error.as_text()],
            warnings=[],
            error_blocks=[error],
            runner_selected="",
            preflight_checks=[],
        )
        return 1, result

    try:
        stop_after_stage = _resolve_stop_after(args)
    except ValueError as exc:
        error = StructuredError(
            reason=str(exc),
            failed_stage="preflight",
            next_action="Adjust --analysis-only/--stop-after flags and rerun.",
        )
        result = make_failure_result(
            started_at=started_at,
            mode=args.mode,
            run_id=run_id,
            stage_summaries=[],
            top_improvements=[],
            message="Invalid stop configuration",
            errors=[error.as_text()],
            warnings=[],
            error_blocks=[error],
            runner_selected="",
            preflight_checks=[],
        )
        return 1, result

    analysis_stage_order = mode_analysis_stage_order[args.mode]
    full_stage_order = analysis_stage_order + IMPLEMENTATION_STAGES
    if args.publish:
        full_stage_order.append("publish")

    if stop_after_stage and stop_after_stage not in full_stage_order:
        error = StructuredError(
            reason=(
                f"Stage '{stop_after_stage}' is not available in mode '{args.mode}'"
                + (" with publish disabled." if stop_after_stage == "publish" else ".")
            ),
            failed_stage="preflight",
            next_action="Choose a stop stage present in this mode, or enable --publish when stopping after publish.",
        )
        result = make_failure_result(
            started_at=started_at,
            mode=args.mode,
            run_id=run_id,
            stage_summaries=[],
            top_improvements=[],
            message="Invalid stop configuration",
            errors=[error.as_text()],
            warnings=[],
            error_blocks=[error],
            runner_selected="",
            preflight_checks=[],
        )
        return 1, result

    required_stages = _slice_required_stages(full_stage_order, stop_after_stage)
    implementation_requested = any(stage in IMPLEMENTATION_STAGES or stage == "publish" for stage in required_stages)

    try:
        runner_adapter, runner_warnings = select_runner(args.runner, args.task_runner_cmd, repo_root)
    except ValueError as exc:
        error = StructuredError(
            reason=str(exc),
            failed_stage="preflight",
            next_action="Adjust --runner/--task-runner-cmd and rerun.",
        )
        result = make_failure_result(
            started_at=started_at,
            mode=args.mode,
            run_id=run_id,
            stage_summaries=[],
            top_improvements=[],
            message="Runner selection failed",
            errors=[error.as_text()],
            warnings=[],
            error_blocks=[error],
            runner_selected="",
            preflight_checks=[],
        )
        return 1, result

    preflight = run_preflight(
        repo_root=repo_root,
        base_branch=args.base_branch,
        allow_dirty=args.allow_dirty,
        publish_requested=args.publish,
        stage_commands=stage_commands,
        required_stages=required_stages,
        runner_selected=runner_adapter.name,
    )

    stage_summaries: List[Dict[str, Any]] = []
    top_improvements: List[Dict[str, Any]] = []
    errors: List[str] = []
    error_blocks: List[StructuredError] = []
    warnings: List[str] = list(runner_warnings) + list(preflight.warnings)
    total_elapsed_ms = 0
    retries = 0

    stage_summaries.append(
        {
            "stage": "preflight",
            "status": "success" if preflight.passed else "failed",
            "elapsed_ms": 0,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status,
                    "detail": c.detail,
                    "next_action": c.next_action,
                }
                for c in preflight.checks
            ],
        }
    )

    if not preflight.passed:
        error_blocks.extend(preflight.errors)
        errors.extend(e.as_text() for e in preflight.errors)
        result = make_failure_result(
            started_at=started_at,
            mode=args.mode,
            run_id=run_id,
            stage_summaries=stage_summaries,
            top_improvements=top_improvements,
            message="Preflight failed. See next_action for recovery steps.",
            errors=errors,
            warnings=warnings,
            error_blocks=error_blocks,
            runner_selected=runner_adapter.name,
            preflight_checks=preflight.checks,
        )
        return 1, result

    analysis_stage_payloads: Dict[str, Dict[str, Any]] = {}
    analysis_stage_paths: Dict[str, str] = {}
    analysis_stage_lineage: List[Dict[str, Any]] = []
    pr_spec_lineage: List[Dict[str, Any]] = []
    pr_stage_lineage: List[Dict[str, Any]] = []
    artifact_root = run_artifact_dir(repo_root, run_id)
    report_path = default_report_path(repo_root, run_id)
    analysis_artifact_dir = default_analysis_artifact_dir(repo_root, run_id)

    with tempfile.TemporaryDirectory(prefix="pr-factory-") as tmp_dir:
        tmp = Path(tmp_dir)
        analysis_artifact_dir.mkdir(parents=True, exist_ok=True)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        template_values: Dict[str, str] = {
            "REPO_ROOT": str(repo_root),
            "REPO_URL": args.repo_url,
            "BASE_BRANCH": args.base_branch,
            "CONTEXT_PATH": args.context_path,
            "FOCUS": args.focus,
            "MODE": args.mode,
            "MAX_PRS": str(args.max_prs),
            "TEMP_DIR": str(tmp),
            "ARTIFACT_DIR": str(analysis_artifact_dir),
            "REPORT_PATH": str(report_path),
            "RUNNER": runner_adapter.name,
        }

        # Analysis path executes once.
        for stage in analysis_stage_order:
            for previous_stage, path in analysis_stage_paths.items():
                template_values[f"{previous_stage.upper()}_JSON"] = path

            run_result, attempts, retry_trace = execute_stage_with_retries(
                adapter=runner_adapter,
                stage=stage,
                command_template=stage_commands[stage],
                cwd=repo_root,
                template_values=template_values,
                max_attempts=1,
            )
            total_elapsed_ms += run_result.elapsed_ms
            if attempts > 1:
                retries += attempts - 1

            summary: Dict[str, Any] = {
                "stage": stage,
                "command": run_result.command,
                "runner": run_result.runner,
                "exit_code": run_result.exit_code,
                "elapsed_ms": run_result.elapsed_ms,
                "attempts": attempts,
                "status": "",
                "retry_trace": retry_trace,
                }

            if run_result.exit_code != 0:
                reason = run_result.stderr.strip() or run_result.stdout.strip() or f"Stage {stage} failed"
                error = StructuredError(
                    reason=reason,
                    failed_stage=stage,
                    next_action=f"Fix stage command/output for '{stage}' and rerun pipeline.",
                )
                error_blocks.append(error)
                errors.append(error.as_text())
                summary["status"] = "failed"
                stage_summaries.append(summary)
                break

            if run_result.payload is None:
                error = StructuredError(
                    reason="missing JSON payload",
                    failed_stage=stage,
                    next_action="Ensure stage prints valid JSON or SAVED_JSON_PATH and rerun.",
                )
                error_blocks.append(error)
                errors.append(error.as_text())
                summary["status"] = "failed"
                stage_summaries.append(summary)
                break

            payload_path = analysis_artifact_dir / f"{stage}.json"
            payload = persist_stage_payload(
                run_result.payload,
                path=payload_path,
                run_id=run_id,
                artifact_root=artifact_root,
                lineage={"stage": stage, "pipeline_mode": args.mode},
            )
            if stage == "critic":
                summary["status"] = critic_decision(payload)
            else:
                summary["status"] = stage_status(payload)
            summary["payload_path"] = str(payload_path)
            stage_summaries.append(summary)
            analysis_stage_payloads[stage] = payload
            analysis_stage_paths[stage] = str(payload_path)
            analysis_stage_lineage.append({"stage": stage, "path": str(payload_path)})

            if stage in {"scout", "analyst", "architect"}:
                collected_improvements = collect_top_improvements(payload)
                if collected_improvements:
                    top_improvements = collected_improvements

            gate_msg = gate_failed(stage, payload)
            if gate_msg:
                error = StructuredError(
                    reason=gate_msg,
                    failed_stage=stage,
                    next_action=f"Address {stage} gate feedback before rerunning.",
                )
                error_blocks.append(error)
                errors.append(error.as_text())
                break

        pr_results: List[Dict[str, Any]] = []
        selected_pr_specs: List[Dict[str, Any]] = []

        if not errors:
            gatekeeper_payload = analysis_stage_payloads.get("gatekeeper", {})
            extracted_pr_specs = extract_pr_specs(gatekeeper_payload)
            if not extracted_pr_specs and "gatekeeper" in analysis_stage_payloads:
                error = StructuredError(
                    reason="Gatekeeper approved PR flow but did not provide pr_spec/pr_specs.",
                    failed_stage="gatekeeper",
                    next_action="Update gatekeeper output to include data.pr_specs[] or pr_spec.",
                )
                error_blocks.append(error)
                errors.append(error.as_text())
            elif extracted_pr_specs:
                max_prs = max(1, int(args.max_prs))
                selected_pr_specs = [
                    normalize_pr_spec(
                        raw_pr_spec=raw_pr_spec,
                        index=index,
                        base_branch=args.base_branch,
                        repo_url=args.repo_url,
                    )
                    for index, raw_pr_spec in enumerate(extracted_pr_specs[:max_prs], start=1)
                ]

                if implementation_requested:
                    for index, normalized_pr_spec in enumerate(selected_pr_specs, start=1):
                        pr_stage_payloads: Dict[str, Dict[str, Any]] = {}
                        pr_stage_summaries: List[Dict[str, Any]] = []
                        pr_errors: List[StructuredError] = []
                        pr_warnings: List[str] = []
                        pr_retry_trace: List[Dict[str, Any]] = []
                        base_sha_at_publish = ""

                        pr_dir = default_pr_artifact_dir(repo_root, run_id, index)
                        pr_dir.mkdir(parents=True, exist_ok=True)
                        prspec_path = pr_dir / "prspec.json"
                        write_json(prspec_path, normalized_pr_spec)
                        pr_spec_lineage.append(
                            {
                                "index": index,
                                "id": normalized_pr_spec.get("id", f"prspec-{index}"),
                                "path": str(prspec_path),
                            }
                        )

                        per_pr_template_values = dict(template_values)
                        per_pr_template_values.update(
                            {
                                "PR_INDEX": str(index),
                                "PRSPEC_JSON": str(prspec_path),
                                "HEAD_BRANCH": str(
                                    ((normalized_pr_spec.get("head") or {}).get("branch") if isinstance(normalized_pr_spec.get("head"), dict) else "")
                                    or ""
                                ),
                                "ARTIFACT_DIR": str(pr_dir),
                            }
                        )

                        pr_stage_order = [stage for stage in IMPLEMENTATION_STAGES if stage in required_stages]
                        if "publish" in required_stages:
                            pr_stage_order.append("publish")

                        for stage in pr_stage_order:
                            for previous_stage, path in analysis_stage_paths.items():
                                per_pr_template_values[f"{previous_stage.upper()}_JSON"] = path

                            for previous_stage, payload in pr_stage_payloads.items():
                                path = pr_dir / f"{previous_stage}.json"
                                persisted_payload = persist_stage_payload(
                                    payload,
                                    path=path,
                                    run_id=run_id,
                                    artifact_root=artifact_root,
                                    lineage={
                                        "stage": previous_stage,
                                        "pipeline_mode": args.mode,
                                        "pr_index": index,
                                        "prspec_path": str(prspec_path),
                                    },
                                )
                                pr_stage_payloads[previous_stage] = persisted_payload
                                per_pr_template_values[f"{previous_stage.upper()}_JSON"] = str(path)

                            if stage == "publish":
                                try:
                                    current_base_sha, _ = resolve_base_sha(
                                        repo_root=repo_root,
                                        base_branch=args.base_branch,
                                        allow_local_fallback=False,
                                    )
                                    base_sha_at_publish = current_base_sha
                                except ValueError as exc:
                                    pr_errors.append(
                                        StructuredError(
                                            reason=str(exc),
                                            failed_stage="publish",
                                            next_action=f"Run `git fetch origin {args.base_branch}` and retry publish.",
                                        )
                                    )
                                    break

                                if preflight.base_sha_at_start and base_sha_at_publish != preflight.base_sha_at_start:
                                    drift_msg = (
                                        f"Base drift detected for PR #{index}: start={preflight.base_sha_at_start}, "
                                        f"publish={base_sha_at_publish}"
                                    )
                                    if args.base_drift_policy == "needs_human":
                                        pr_errors.append(
                                            StructuredError(
                                                reason=drift_msg,
                                                failed_stage="publish",
                                                next_action=(
                                                    f"Rebase/cherry-pick on latest origin/{args.base_branch} and rerun publish."
                                                ),
                                            )
                                        )
                                        break
                                    if args.base_drift_policy == "warn":
                                        pr_warnings.append(drift_msg)

                            max_attempts = args.implement_max_attempts if stage == "implement" else 1
                            run_result, attempts, retry_trace = execute_stage_with_retries(
                                adapter=runner_adapter,
                                stage=stage,
                                command_template=stage_commands[stage],
                                cwd=repo_root,
                                template_values=per_pr_template_values,
                                max_attempts=max_attempts,
                            )
                            total_elapsed_ms += run_result.elapsed_ms
                            if attempts > 1:
                                retries += attempts - 1
                            pr_retry_trace.extend(retry_trace)

                            stage_summary = {
                                "stage": stage,
                                "command": run_result.command,
                                "runner": run_result.runner,
                                "exit_code": run_result.exit_code,
                                "elapsed_ms": run_result.elapsed_ms,
                                "attempts": attempts,
                                "status": "",
                                "retry_trace": retry_trace,
                            }

                            if run_result.exit_code != 0:
                                reason = run_result.stderr.strip() or run_result.stdout.strip() or f"Stage {stage} failed"
                                pr_errors.append(
                                    StructuredError(
                                        reason=reason,
                                        failed_stage=stage,
                                        next_action=f"Fix stage output/command for '{stage}' and rerun this PRSpec.",
                                    )
                                )
                                stage_summary["status"] = "failed"
                                pr_stage_summaries.append(stage_summary)
                                break

                            if run_result.payload is None:
                                pr_errors.append(
                                    StructuredError(
                                        reason="missing JSON payload",
                                        failed_stage=stage,
                                        next_action="Ensure stage prints valid JSON output.",
                                    )
                                )
                                stage_summary["status"] = "failed"
                                pr_stage_summaries.append(stage_summary)
                                break

                            payload_path = pr_dir / f"{stage}.json"
                            payload = persist_stage_payload(
                                run_result.payload,
                                path=payload_path,
                                run_id=run_id,
                                artifact_root=artifact_root,
                                lineage={
                                    "stage": stage,
                                    "pipeline_mode": args.mode,
                                    "pr_index": index,
                                    "prspec_path": str(prspec_path),
                                },
                            )
                            stage_summary["status"] = stage_status(payload)
                            stage_summary["payload_path"] = str(payload_path)
                            pr_stage_summaries.append(stage_summary)
                            pr_stage_payloads[stage] = payload
                            pr_stage_lineage.append({"index": index, "stage": stage, "path": str(payload_path)})

                            gate_msg = gate_failed(stage, payload)
                            if gate_msg:
                                pr_errors.append(
                                    StructuredError(
                                        reason=gate_msg,
                                        failed_stage=stage,
                                        next_action=f"Address '{stage}' findings and retry this PRSpec.",
                                    )
                                )
                                break

                            if stage == "pr_writer":
                                maybe_final = payload.get("pr_spec")
                                if isinstance(maybe_final, dict) and maybe_final:
                                    normalized_pr_spec = normalize_pr_spec(
                                        raw_pr_spec=maybe_final,
                                        index=index,
                                        base_branch=args.base_branch,
                                        repo_url=args.repo_url,
                                    )
                                    selected_pr_specs[index - 1] = normalized_pr_spec
                                    write_json(prspec_path, normalized_pr_spec)
                                    per_pr_template_values["PRSPEC_JSON"] = str(prspec_path)
                                    per_pr_template_values["HEAD_BRANCH"] = str(
                                        ((normalized_pr_spec.get("head") or {}).get("branch") if isinstance(normalized_pr_spec.get("head"), dict) else "")
                                        or ""
                                    )

                        pr_status = "success" if not pr_errors else "needs_human"
                        publish_payload = pr_stage_payloads.get("publish", {})
                        pr_url = ""
                        if isinstance(publish_payload, dict):
                            data = publish_payload.get("data", {})
                            if isinstance(data, dict):
                                pr_data = data.get("pr", {})
                                if isinstance(pr_data, dict):
                                    pr_url = str(pr_data.get("url") or "")

                        final_pr_message: Dict[str, Any] = {}
                        title = normalized_pr_spec.get("title")
                        body_markdown = normalized_pr_spec.get("body_markdown")
                        if isinstance(title, str) and isinstance(body_markdown, str):
                            final_pr_message = {"title": title, "body_markdown": body_markdown}

                        pr_results.append(
                            {
                                "index": index,
                                "id": normalized_pr_spec.get("id", f"prspec-{index}"),
                                "status": pr_status,
                                "stage_summary": pr_stage_summaries,
                                "errors": [e.as_text() for e in pr_errors],
                                "warnings": pr_warnings,
                                "retry_trace": pr_retry_trace,
                                "pr_spec": normalized_pr_spec,
                                "final_pr_message": final_pr_message,
                                "publish": {
                                    "requested": bool(args.publish),
                                    "url": pr_url,
                                },
                                "lineage": {
                                    "prspec_path": str(prspec_path),
                                    "stage_payloads": [item for item in pr_stage_lineage if item.get("index") == index],
                                },
                                "base_sha_at_start": preflight.base_sha_at_start,
                                "base_sha_at_publish": base_sha_at_publish,
                            }
                        )

                        error_blocks.extend(pr_errors)
                        errors.extend(e.as_text() for e in pr_errors)
                        warnings.extend(pr_warnings)

        successful_prs = [item for item in pr_results if item.get("status") == "success"]
        first_pr = successful_prs[0] if successful_prs else (pr_results[0] if pr_results else {})
        final_pr_spec = first_pr.get("pr_spec", {}) if isinstance(first_pr, dict) else {}
        if not final_pr_spec and selected_pr_specs:
            final_pr_spec = selected_pr_specs[0]

        status = "success" if not errors else "needs_human"
        summary = "Completed deterministic pipeline run."
        if errors:
            summary = "Stopped pipeline with one or more recoverable failures."
        elif stop_after_stage:
            summary = f"Completed deterministic pipeline run and stopped after {stop_after_stage}."

        pipeline_id = pipeline_id_for_run(run_id)
        if args.summary_output:
            summary_path = Path(args.summary_output).resolve()
        else:
            summary_path = default_artifact_dir(repo_root) / f"pipeline-summary-{pipeline_id}.json"

        lineage = {
            "artifact_root": str(artifact_root),
            "summary_path": str(summary_path),
            "report_path": str(report_path),
            "analysis_stage_payloads": analysis_stage_lineage,
            "pr_specs": pr_spec_lineage,
            "pr_stage_payloads": pr_stage_lineage,
        }
        summary_payload = {
            "schema_version": "1.0",
            "id": pipeline_id,
            "run_id": run_id,
            "generated_at": utc_now(),
            "pipeline_mode": args.mode,
            "runner_selected": runner_adapter.name,
            "status": status,
            "lineage": lineage,
            "preflight": {
                "passed": preflight.passed,
                "base_sha_at_start": preflight.base_sha_at_start,
                "checks": [
                    {
                        "name": c.name,
                        "status": c.status,
                        "detail": c.detail,
                        "next_action": c.next_action,
                    }
                    for c in preflight.checks
                ],
            },
            "stage_durations": [
                {
                    "stage": item.get("stage"),
                    "elapsed_ms": item.get("elapsed_ms", 0),
                }
                for item in stage_summaries
            ],
            "pr_results": [
                {
                    "index": item.get("index"),
                    "id": item.get("id"),
                    "status": item.get("status"),
                    "publish_url": ((item.get("publish") or {}).get("url") if isinstance(item.get("publish"), dict) else ""),
                    "base_sha_at_start": item.get("base_sha_at_start", ""),
                    "base_sha_at_publish": item.get("base_sha_at_publish", ""),
                }
                for item in pr_results
            ],
            "errors": [e.as_dict() for e in error_blocks],
            "warnings": warnings,
        }

        summary_path_str = ""
        try:
            validate_pipeline_summary(summary_payload)
        except SchemaValidationError as exc:
            error = StructuredError(
                reason=str(exc),
                failed_stage="pipeline_summary",
                next_action="Fix pipeline summary assembly before rerunning.",
            )
            error_blocks.append(error)
            errors.append(error.as_text())
            result = make_failure_result(
                started_at=started_at,
                mode=args.mode,
                run_id=run_id,
                stage_summaries=stage_summaries,
                top_improvements=top_improvements,
                message="Pipeline summary validation failed",
                errors=errors,
                warnings=warnings,
                error_blocks=error_blocks,
                runner_selected=runner_adapter.name,
                preflight_checks=preflight.checks,
                pr_results=pr_results,
                summary_path=str(summary_path),
                lineage=lineage,
                final_pr_spec=final_pr_spec if isinstance(final_pr_spec, dict) else None,
                selected_pr_specs=selected_pr_specs,
                report_path=str(report_path),
            )
            return 1, result
        try:
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            write_json(summary_path, summary_payload)
            summary_path_str = str(summary_path)
        except OSError as exc:
            warnings.append(f"Failed to write pipeline summary: {exc}")

        final_pr_message: Dict[str, Any] = {}
        if isinstance(final_pr_spec, dict):
            title = final_pr_spec.get("title")
            body_markdown = final_pr_spec.get("body_markdown")
            if isinstance(title, str) and isinstance(body_markdown, str):
                final_pr_message = {"title": title, "body_markdown": body_markdown}

        result: Dict[str, Any] = {
            "schema_version": "1.0",
            "id": pipeline_id,
            "stage": "pipeline",
            "status": status,
            "summary": summary,
            "started_at": started_at,
            "finished_at": utc_now(),
            "exit_code": 0 if status == "success" else 1,
            "stdout": "",
            "stderr": "\n".join(errors),
            "artifacts": _build_pipeline_artifacts(summary_path=summary_path_str, report_path=str(report_path)),
            "metrics": {
                "duration_ms": total_elapsed_ms,
                "cost_usd": 0.0,
                "tokens_in": 0,
                "tokens_out": 0,
                "retries": retries,
            },
            "errors": errors,
            "warnings": warnings,
            "data": {
                "pipeline_mode": args.mode,
                "run_id": run_id,
                "runner_selected": runner_adapter.name,
                "stop_after_stage": stop_after_stage,
                "stage_summary": stage_summaries,
                "top_improvements": top_improvements,
                "selected_prspec": final_pr_spec if isinstance(final_pr_spec, dict) else {},
                "selected_prspecs": [
                    item
                    for item in (
                        [item.get("pr_spec", {}) for item in pr_results if isinstance(item, dict)]
                        or selected_pr_specs
                    )
                    if isinstance(item, dict)
                ],
                "final_pr_message": final_pr_message,
                "pr_results": pr_results,
                "report_path": str(report_path),
                "preflight": {
                    "checks": [
                        {
                            "name": c.name,
                            "status": c.status,
                            "detail": c.detail,
                            "next_action": c.next_action,
                        }
                        for c in preflight.checks
                    ],
                    "base_sha_at_start": preflight.base_sha_at_start,
                },
                "error_blocks": [e.as_dict() for e in error_blocks],
                "lineage": {**lineage, "summary_path": summary_path_str or lineage["summary_path"]},
                "pipeline_summary_path": summary_path_str,
            },
            "pr_spec": final_pr_spec if isinstance(final_pr_spec, dict) else {},
        }

    return (0 if result["status"] == "success" else 1), result


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    exit_code, result = run_pipeline(args)

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output + "\n", encoding="utf-8")
    print(output)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
