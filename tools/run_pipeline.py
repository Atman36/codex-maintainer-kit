#!/usr/bin/env python3
"""
Deterministic PR Factory orchestrator.

This script executes stage commands in strict order, enforces gate decisions, and
adds a self-healing retry loop for the Implementer stage.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


MODE_STAGE_ORDER: Dict[str, List[str]] = {
    "full": ["scout", "analyst", "critic", "gatekeeper", "implement", "reviewer", "pr_writer"],
    "quick-win": ["scout", "gatekeeper", "implement", "reviewer", "pr_writer"],
    "architecture": ["architect", "critic", "gatekeeper", "implement", "reviewer", "pr_writer"],
}


@dataclass
class StageRun:
    stage: str
    command: str
    exit_code: int
    stdout: str
    stderr: str
    payload: Optional[Dict[str, Any]]
    elapsed_ms: int


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


def parse_json_output(stdout: str) -> Dict[str, Any]:
    text = stdout.strip()
    if not text:
        raise ValueError("Stage produced empty stdout; expected JSON.")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Stage stdout is not valid JSON: {exc}") from exc


def run_stage(stage: str,
              command_template: str,
              cwd: Path,
              template_values: Dict[str, str],
              extra_env: Optional[Dict[str, str]] = None) -> StageRun:
    command = expand_template(command_template, template_values)
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    started = time.time()
    proc = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        shell=True,
        capture_output=True,
        text=True,
    )
    elapsed_ms = int((time.time() - started) * 1000)

    payload: Optional[Dict[str, Any]] = None
    if proc.returncode == 0:
        payload = parse_json_output(proc.stdout)
    return StageRun(
        stage=stage,
        command=command,
        exit_code=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        payload=payload,
        elapsed_ms=elapsed_ms,
    )


def stage_status(payload: Dict[str, Any]) -> str:
    return str(payload.get("status", "")).strip().lower()


def critic_decision(payload: Dict[str, Any]) -> str:
    return str(payload.get("decision", "")).strip().lower()


def gatekeeper_decision(payload: Dict[str, Any]) -> str:
    data = payload.get("data", {})
    if isinstance(data, dict):
        selected = data.get("selected")
        if isinstance(selected, list):
            decisions: List[str] = []
            for item in selected:
                if isinstance(item, dict):
                    decision = str(item.get("decision", "")).strip().lower()
                    if decision:
                        decisions.append(decision)
            if "pr" in decisions:
                return "pr"
            if decisions:
                return decisions[0]
    if payload.get("pr_spec"):
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


def make_failure_result(started_at: str,
                        mode: str,
                        summaries: List[Dict[str, Any]],
                        top_improvements: List[Dict[str, Any]],
                        message: str,
                        errors: List[str],
                        pr_spec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
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
        "artifacts": [],
        "metrics": {
            "duration_ms": 0,
            "cost_usd": 0.0,
            "tokens_in": 0,
            "tokens_out": 0,
            "retries": 0,
        },
        "errors": errors,
        "warnings": [],
        "data": {
            "pipeline_mode": mode,
            "stage_summary": summaries,
            "top_improvements": top_improvements,
            "selected_prspec": pr_spec or {},
            "final_pr_message": {},
        },
        "pr_spec": pr_spec or {},
    }


def collect_top_improvements(stage_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = stage_payload.get("data", {})
    if isinstance(data, dict):
        candidates = data.get("candidates")
        if isinstance(candidates, list):
            return [c for c in candidates if isinstance(c, dict)]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic PR Factory pipeline runner.")
    parser.add_argument("--repo-root", required=True, help="Absolute path to repository root.")
    parser.add_argument("--repo-url", default="", help="Repository URL.")
    parser.add_argument("--base-branch", default="main", help="Base branch.")
    parser.add_argument("--context-path", default="", help="Optional context path.")
    parser.add_argument("--focus", default="", help="Optional focus value for Analyst.")
    parser.add_argument("--mode", choices=sorted(MODE_STAGE_ORDER.keys()), default="full")
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
    parser.add_argument("--output", default="", help="Write final JSON to this file.")
    args = parser.parse_args()

    started_at = utc_now()
    repo_root = Path(args.repo_root).resolve()
    if not repo_root.exists():
        raise SystemExit(f"Repository root not found: {repo_root}")

    stage_commands = parse_stage_commands(args.stage_command)
    stages = MODE_STAGE_ORDER[args.mode][:]
    if args.publish:
        stages.append("publish")

    stage_summaries: List[Dict[str, Any]] = []
    stage_payloads: Dict[str, Dict[str, Any]] = {}
    top_improvements: List[Dict[str, Any]] = []
    errors: List[str] = []
    total_elapsed_ms = 0
    retries = 0

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

        for stage in stages:
            if stage not in stage_commands:
                result = make_failure_result(
                    started_at,
                    args.mode,
                    stage_summaries,
                    top_improvements,
                    f"Missing stage command for '{stage}'",
                    [f"No --stage-command provided for stage '{stage}'"],
                    stage_payloads.get("pr_writer", {}).get("pr_spec"),
                )
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 1

            # Persist prior payloads so command templates can consume file paths.
            for previous_stage, payload in stage_payloads.items():
                path = tmp / f"{previous_stage}.json"
                path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                template_values[f"{previous_stage.upper()}_JSON"] = str(path)

            attempt = 0
            max_attempts = args.implement_max_attempts if stage == "implement" else 1
            stage_run: Optional[StageRun] = None
            last_error_text = ""
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
                        stage=stage,
                        command_template=stage_commands[stage],
                        cwd=repo_root,
                        template_values=template_values,
                        extra_env=extra_env,
                    )
                except ValueError as exc:
                    run_result = StageRun(
                        stage=stage,
                        command=expand_template(stage_commands[stage], template_values),
                        exit_code=1,
                        stdout="",
                        stderr=str(exc),
                        payload=None,
                        elapsed_ms=0,
                    )
                total_elapsed_ms += run_result.elapsed_ms
                stage_run = run_result

                if run_result.exit_code != 0:
                    last_error_text = (run_result.stderr or run_result.stdout).strip()
                    if stage == "implement" and attempt < max_attempts:
                        retries += 1
                        continue
                    break

                assert run_result.payload is not None
                if stage == "implement":
                    status = stage_status(run_result.payload)
                    if status in {"retryable", "failed"} and attempt < max_attempts:
                        retries += 1
                        last_error_text = str(run_result.payload.get("stderr", "") or run_result.stderr or "")
                        continue
                break

            if stage_run is None:
                raise RuntimeError("Internal error: stage did not run")

            summary: Dict[str, Any] = {
                "stage": stage,
                "command": stage_run.command,
                "exit_code": stage_run.exit_code,
                "elapsed_ms": stage_run.elapsed_ms,
                "attempts": attempt,
                "status": "",
            }

            if stage_run.exit_code != 0:
                err = stage_run.stderr.strip() or stage_run.stdout.strip() or f"Stage {stage} failed"
                errors.append(f"{stage}: {err}")
                summary["status"] = "failed"
                stage_summaries.append(summary)
                break

            payload = stage_run.payload
            if payload is None:
                errors.append(f"{stage}: missing JSON payload")
                summary["status"] = "failed"
                stage_summaries.append(summary)
                break

            if stage == "critic":
                summary["status"] = critic_decision(payload)
            else:
                summary["status"] = stage_status(payload)
            stage_summaries.append(summary)
            stage_payloads[stage] = payload

            if stage == "scout":
                top_improvements = collect_top_improvements(payload)

            gate_msg = gate_failed(stage, payload)
            if gate_msg:
                errors.append(gate_msg)
                break

    pr_writer_payload = stage_payloads.get("pr_writer", {})
    final_pr_spec = pr_writer_payload.get("pr_spec") if isinstance(pr_writer_payload, dict) else {}
    final_pr_message: Dict[str, Any] = {}
    if isinstance(final_pr_spec, dict):
        title = final_pr_spec.get("title")
        body_markdown = final_pr_spec.get("body_markdown")
        if isinstance(title, str) and isinstance(body_markdown, str):
            final_pr_message = {"title": title, "body_markdown": body_markdown}

    status = "success" if not errors else "needs_human"
    summary = "Completed deterministic pipeline run."
    if errors:
        summary = f"Stopped pipeline due to gate/command failure: {errors[-1]}"

    result: Dict[str, Any] = {
        "schema_version": "1.0",
        "id": f"pipeline-{int(time.time())}",
        "stage": "pipeline",
        "status": status,
        "summary": summary,
        "started_at": started_at,
        "finished_at": utc_now(),
        "exit_code": 0 if status == "success" else 1,
        "stdout": "",
        "stderr": "\n".join(errors),
        "artifacts": [],
        "metrics": {
            "duration_ms": total_elapsed_ms,
            "cost_usd": 0.0,
            "tokens_in": 0,
            "tokens_out": 0,
            "retries": retries,
        },
        "errors": errors,
        "warnings": [],
        "data": {
            "pipeline_mode": args.mode,
            "stage_summary": stage_summaries,
            "top_improvements": top_improvements,
            "selected_prspec": final_pr_spec if isinstance(final_pr_spec, dict) else {},
            "final_pr_message": final_pr_message,
        },
        "pr_spec": final_pr_spec if isinstance(final_pr_spec, dict) else {},
    }

    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output).resolve()
        output_path.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0 if status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
