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
from dataclasses import dataclass
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


MODE_ANALYSIS_STAGE_ORDER: Dict[str, List[str]] = {
    "full": ["scout", "analyst", "critic", "gatekeeper"],
    "quick-win": ["scout", "gatekeeper"],
    "architecture": ["architect", "critic", "gatekeeper"],
}

IMPLEMENTATION_STAGES: List[str] = ["implement", "reviewer", "pr_writer"]


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
    out = template
    for k, v in values.items():
        out = out.replace("{{" + k + "}}", v)
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
        refs.append(base_branch)
    for ref in refs:
        proc = run_git(["rev-parse", "--verify", ref], cwd=repo_root)
        if proc.returncode == 0:
            return proc.stdout.strip(), ref
    if allow_local_fallback:
        raise ValueError(
            f"Cannot resolve base SHA for '{base_branch}'. Tried origin/{base_branch} and local {base_branch}."
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
        if decision != "pr":
            return f"Gatekeeper gate failed: decision={decision or 'missing'}"
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
            return [c for c in candidates if isinstance(c, dict)]
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
    if origin.returncode != 0:
        fail(
            "remotes",
            "Missing required remote 'origin'.",
            "Add upstream remote: `git remote add origin <url>`.",
        )
        return PreflightResult(False, checks, errors, warnings, base_sha_at_start, runner_selected)
    ok("remotes", f"origin={origin.stdout.strip()}")

    try:
        base_sha_at_start, base_ref_used = resolve_base_sha(
            repo_root=repo_root,
            base_branch=base_branch,
            allow_local_fallback=False,
        )
        ok("base_sha", f"base_sha_at_start={base_sha_at_start} ({base_ref_used})")
    except ValueError as exc:
        fail(
            "base_sha",
            str(exc),
            f"Run `git fetch origin {base_branch}` and ensure the branch exists.",
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
        except ValueError as exc:
            run_result = StageRun(
                stage=stage,
                command=adapter.build_command(stage=stage, expanded_command=expand_template(command_template, template_values)),
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


def make_failure_result(
    started_at: str,
    mode: str,
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
    final_pr_spec: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    pr_results = pr_results or []
    first_pr_spec = final_pr_spec or {}

    final_pr_message: Dict[str, Any] = {}
    if isinstance(first_pr_spec, dict):
        title = first_pr_spec.get("title")
        body_markdown = first_pr_spec.get("body_markdown")
        if isinstance(title, str) and isinstance(body_markdown, str):
            final_pr_message = {"title": title, "body_markdown": body_markdown}

    return {
        "schema_version": "1.0",
        "id": f"pipeline-{int(time.time())}",
        "stage": "pipeline",
        "status": "needs_human",
        "summary": message,
        "started_at": started_at,
        "finished_at": utc_now(),
        "exit_code": 1,
        "stdout": "",
        "stderr": "\n".join(errors),
        "artifacts": [{"kind": "pipeline_summary", "path": summary_path}] if summary_path else [],
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
            "runner_selected": runner_selected,
            "stage_summary": stage_summaries,
            "top_improvements": top_improvements,
            "selected_prspec": first_pr_spec if isinstance(first_pr_spec, dict) else {},
            "selected_prspecs": [r.get("pr_spec", {}) for r in pr_results if isinstance(r, dict)],
            "final_pr_message": final_pr_message,
            "pr_results": pr_results,
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
    parser.add_argument("--mode", choices=sorted(MODE_ANALYSIS_STAGE_ORDER.keys()), default="full")
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
    return parser.parse_args(argv)


def run_pipeline(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    started_at = utc_now()
    repo_root = Path(args.repo_root).resolve()

    try:
        stage_commands = parse_stage_commands(args.stage_command)
    except ValueError as exc:
        result = make_failure_result(
            started_at=started_at,
            mode=args.mode,
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

    required_stages = MODE_ANALYSIS_STAGE_ORDER[args.mode] + IMPLEMENTATION_STAGES
    if args.publish:
        required_stages.append("publish")

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

    with tempfile.TemporaryDirectory(prefix="pr-factory-") as tmp_dir:
        tmp = Path(tmp_dir)
        template_values: Dict[str, str] = {
            "REPO_ROOT": str(repo_root),
            "REPO_URL": args.repo_url,
            "BASE_BRANCH": args.base_branch,
            "CONTEXT_PATH": args.context_path,
            "FOCUS": args.focus,
            "MODE": args.mode,
            "MAX_PRS": str(args.max_prs),
            "TEMP_DIR": str(tmp),
        }

        # Analysis path executes once.
        for stage in MODE_ANALYSIS_STAGE_ORDER[args.mode]:
            for previous_stage, payload in analysis_stage_payloads.items():
                path = tmp / f"{previous_stage}.json"
                write_json(path, payload)
                template_values[f"{previous_stage.upper()}_JSON"] = str(path)

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

            payload = run_result.payload
            if stage == "critic":
                summary["status"] = critic_decision(payload)
            else:
                summary["status"] = stage_status(payload)
            stage_summaries.append(summary)
            analysis_stage_payloads[stage] = payload

            if stage == "scout":
                top_improvements = collect_top_improvements(payload)

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

        if not errors:
            gatekeeper_payload = analysis_stage_payloads.get("gatekeeper", {})
            extracted_pr_specs = extract_pr_specs(gatekeeper_payload)
            if not extracted_pr_specs:
                error = StructuredError(
                    reason="Gatekeeper approved PR flow but did not provide pr_spec/pr_specs.",
                    failed_stage="gatekeeper",
                    next_action="Update gatekeeper output to include data.pr_specs[] or pr_spec.",
                )
                error_blocks.append(error)
                errors.append(error.as_text())
            else:
                max_prs = max(1, int(args.max_prs))
                extracted_pr_specs = extracted_pr_specs[:max_prs]

                for index, raw_pr_spec in enumerate(extracted_pr_specs, start=1):
                    normalized_pr_spec = normalize_pr_spec(
                        raw_pr_spec=raw_pr_spec,
                        index=index,
                        base_branch=args.base_branch,
                        repo_url=args.repo_url,
                    )

                    pr_stage_payloads: Dict[str, Dict[str, Any]] = {}
                    pr_stage_summaries: List[Dict[str, Any]] = []
                    pr_errors: List[StructuredError] = []
                    pr_warnings: List[str] = []
                    pr_retry_trace: List[Dict[str, Any]] = []
                    base_sha_at_publish = ""

                    pr_dir = tmp / f"pr-{index}"
                    pr_dir.mkdir(parents=True, exist_ok=True)
                    prspec_path = pr_dir / "prspec.json"
                    write_json(prspec_path, normalized_pr_spec)

                    per_pr_template_values = dict(template_values)
                    per_pr_template_values.update(
                        {
                            "PR_INDEX": str(index),
                            "PRSPEC_JSON": str(prspec_path),
                            "HEAD_BRANCH": str(
                                ((normalized_pr_spec.get("head") or {}).get("branch") if isinstance(normalized_pr_spec.get("head"), dict) else "")
                                or ""
                            ),
                        }
                    )

                    pr_stage_order = list(IMPLEMENTATION_STAGES)
                    if args.publish:
                        pr_stage_order.append("publish")

                    for stage in pr_stage_order:
                        for previous_stage, payload in analysis_stage_payloads.items():
                            path = pr_dir / f"analysis-{previous_stage}.json"
                            write_json(path, payload)
                            per_pr_template_values[f"{previous_stage.upper()}_JSON"] = str(path)

                        for previous_stage, payload in pr_stage_payloads.items():
                            path = pr_dir / f"{previous_stage}.json"
                            write_json(path, payload)
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

                        payload = run_result.payload
                        stage_summary["status"] = stage_status(payload)
                        pr_stage_summaries.append(stage_summary)
                        pr_stage_payloads[stage] = payload

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

        status = "success" if not errors else "needs_human"
        summary = "Completed deterministic pipeline run."
        if errors:
            summary = "Stopped pipeline with one or more recoverable failures."

        pipeline_id = f"pipeline-{int(time.time())}"
        summary_payload = {
            "schema_version": "1.0",
            "id": pipeline_id,
            "generated_at": utc_now(),
            "pipeline_mode": args.mode,
            "runner_selected": runner_adapter.name,
            "status": status,
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

        if args.summary_output:
            summary_path = Path(args.summary_output).resolve()
        else:
            default_summary_dir = Path.cwd() / "analysis_report"
            if not default_summary_dir.exists():
                default_summary_dir = Path.cwd()
            summary_path = default_summary_dir / f"pipeline-summary-{pipeline_id}.json"

        summary_path_str = ""
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
            "artifacts": [{"kind": "pipeline_summary", "path": summary_path_str}] if summary_path_str else [],
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
                "runner_selected": runner_adapter.name,
                "stage_summary": stage_summaries,
                "top_improvements": top_improvements,
                "selected_prspec": final_pr_spec if isinstance(final_pr_spec, dict) else {},
                "selected_prspecs": [item.get("pr_spec", {}) for item in pr_results if isinstance(item, dict)],
                "final_pr_message": final_pr_message,
                "pr_results": pr_results,
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
