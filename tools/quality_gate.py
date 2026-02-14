#!/usr/bin/env python3
"""
quality_gate.py — pre-publish checks for a PR factory.

Includes:
- forbidden files scanner (paths + simple secret-ish patterns)
- merge probability heuristic (local signals + PRSpec + diff stats)

No third-party deps; Python 3.10+.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure `tools/` is on sys.path so this script works both as:
# - `python tools/quality_gate.py ...`
# - imported/executed from other working directories
TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from pr_factory_lib.git_utils import git_status_entries, git_status_paths, is_git_repo, run_git  # noqa: E402

DEFAULT_FORBIDDEN_GLOBS = [
    ".agentplane/**",
    ".opencode/**",
    ".claude/**",
    ".kimi/**",
    ".aider*",
    ".plandex/**",
    ".openhands/**",
    ".openclaw/**",
    "**/.DS_Store",
    "**/*.local.*",
    "**/*.env",
    "**/*.env.*",
    "**/*secrets*",
    "**/*secret*",
    "**/*token*",
    "**/*apikey*",
    "**/*api_key*",
]

# Lightweight "likely secret" patterns. Keep conservative to reduce false positives.
SECRET_REGEXES = [
    re.compile(r"-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----"),
    re.compile(r"\bghp_[A-Za-z0-9]{30,}\b"),  # old GitHub PAT
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # AWS Access Key ID
    re.compile(r"\bAIzaSy[A-Za-z0-9_-]{20,}\b"),  # Google API key (rough)
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),  # Slack token (rough)
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),  # OpenAI-ish (rough; may FP)
]

TEXT_FILE_MAX_BYTES = 512_000  # 512KB


def glob_match(path: str, pattern: str) -> bool:
    # Support ** by just using fnmatch (works reasonably for our patterns)
    return fnmatch.fnmatch(path, pattern)


def scan_forbidden_paths(repo_root: Path,
                         candidate_paths: Optional[List[str]] = None,
                         forbidden_globs: Optional[List[str]] = None) -> List[str]:
    forbidden_globs = forbidden_globs or DEFAULT_FORBIDDEN_GLOBS
    if candidate_paths is None:
        # scan whole tree (excluding .git)
        candidate_paths = []
        for p in repo_root.rglob("*"):
            if ".git" in p.parts:
                continue
            if p.is_file():
                candidate_paths.append(str(p.relative_to(repo_root)).replace("\\", "/"))
    bad: List[str] = []
    for rel in candidate_paths:
        rel_norm = rel.replace("\\", "/")
        for pat in forbidden_globs:
            if glob_match(rel_norm, pat):
                bad.append(rel_norm)
                break
    return sorted(set(bad))


def looks_binary(data: bytes) -> bool:
    if b"\x00" in data[:2048]:
        return True
    return False


def scan_for_secrets(repo_root: Path,
                     candidate_paths: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Naive content scan for secret-ish strings in changed files.
    Returns list of findings: {path, rule, snippet}
    """
    if candidate_paths is None:
        candidate_paths = git_status_paths(repo_root)
    findings: List[Dict[str, Any]] = []
    for rel in candidate_paths:
        abs_path = repo_root / rel
        if not abs_path.exists() or not abs_path.is_file():
            continue
        try:
            data = abs_path.read_bytes()
        except Exception:
            continue
        if len(data) > TEXT_FILE_MAX_BYTES or looks_binary(data):
            continue
        text = data.decode("utf-8", errors="replace")
        for rx in SECRET_REGEXES:
            m = rx.search(text)
            if m:
                snippet = m.group(0)
                # Keep snippet short to avoid exposing secrets in logs
                if len(snippet) > 12:
                    snippet = snippet[:6] + "…" + snippet[-4:]
                findings.append({"path": rel, "rule": rx.pattern, "snippet": snippet})
    return findings


@dataclass
class DiffStats:
    files: int
    insertions: int
    deletions: int
    paths: List[str]


def git_diff_stats(repo_root: Path, base_ref: str = "HEAD") -> DiffStats:
    """
    Compute diff stats for working tree vs base_ref.
    Uses `git diff --numstat <base_ref>`.
    """
    if not is_git_repo(repo_root):
        return DiffStats(files=0, insertions=0, deletions=0, paths=[])

    p = run_git(["diff", "--numstat", base_ref], cwd=repo_root)
    files = 0
    ins = 0
    dels = 0
    paths: List[str] = []
    for line in p.stdout.splitlines():
        if not line.strip():
            continue
        a, d, path = line.split("\t", 2)
        if a.isdigit():
            ins += int(a)
        if d.isdigit():
            dels += int(d)
        files += 1
        paths.append(path.strip())
    return DiffStats(files=files, insertions=ins, deletions=dels, paths=paths)


def repo_signals(repo_root: Path) -> Dict[str, Any]:
    """
    Local-only signals about repo maturity.
    """
    ci = (repo_root / ".github" / "workflows").exists()
    contributing = (repo_root / "CONTRIBUTING.md").exists()
    codeowners = (repo_root / ".github" / "CODEOWNERS").exists() or (repo_root / "CODEOWNERS").exists()
    has_tests = any((repo_root / p).exists() for p in ["tests", "test", "__tests__", "spec", "pytest.ini"])
    has_linters = any((repo_root / p).exists() for p in [".ruff.toml", "ruff.toml", ".eslintrc", ".eslintrc.json", ".flake8", "pyproject.toml"])
    has_precommit = (repo_root / ".pre-commit-config.yaml").exists()
    return {
        "ci_detected": ci,
        "contributing_detected": contributing,
        "codeowners_detected": codeowners,
        "tests_detected": has_tests,
        "linters_detected": has_linters,
        "precommit_detected": has_precommit,
    }


def classify_paths(paths: List[str]) -> Dict[str, int]:
    """
    Rough classification for mergeability scoring.
    """
    buckets = {
        "docs": 0, "tests": 0, "ci": 0, "src": 0, "build": 0, "configs": 0, "other": 0
    }
    for p in paths:
        pn = p.lower()
        if any(k in pn for k in ["readme", "docs/", "doc/", ".md", ".rst"]):
            buckets["docs"] += 1
        elif any(k in pn for k in ["test", "spec", "__tests__", "pytest"]):
            buckets["tests"] += 1
        elif pn.startswith(".github/workflows/") or pn.endswith(".yml") or pn.endswith(".yaml") and ".github" in pn:
            buckets["ci"] += 1
        elif any(pn.endswith(x) for x in [".lock", "package.json", "pyproject.toml", "requirements.txt", "go.mod"]):
            buckets["build"] += 1
        elif any(pn.endswith(x) for x in [".toml", ".ini", ".cfg", ".editorconfig"]) or pn.startswith(".github/"):
            buckets["configs"] += 1
        elif any(pn.endswith(x) for x in [".py", ".js", ".ts", ".go", ".rs", ".java", ".kt", ".cs", ".cpp", ".c", ".h"]):
            buckets["src"] += 1
        else:
            buckets["other"] += 1
    return buckets


def merge_probability(prspec: Optional[Dict[str, Any]],
                      diff: DiffStats,
                      signals: Dict[str, Any],
                      forbidden_hits: List[str],
                      secret_hits: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Produces a heuristic probability in [0,1] plus reasons and blockers.

    This is intentionally conservative and local-only.
    """
    score = 0.50
    reasons: List[str] = []
    blockers: List[str] = []

    # Blockers first
    if secret_hits:
        blockers.append("Potential secret/token material detected in changed files.")
        score -= 0.60
    if forbidden_hits:
        blockers.append("Forbidden tool state files/directories are present in the worktree.")
        score -= 0.40

    # Diff size
    loc = diff.insertions + diff.deletions
    if loc <= 80:
        score += 0.12; reasons.append("Very small diff (≤80 LOC).")
    elif loc <= 200:
        score += 0.06; reasons.append("Small diff (≤200 LOC).")
    elif loc <= 600:
        score -= 0.08; reasons.append("Medium diff (≤600 LOC).")
    else:
        score -= 0.18; reasons.append("Large diff (>600 LOC).")

    # File types
    buckets = classify_paths(diff.paths)
    if buckets["docs"] and not buckets["src"]:
        score += 0.10; reasons.append("Docs-only change.")
    if buckets["tests"] and not buckets["build"]:
        score += 0.06; reasons.append("Includes tests.")
    if buckets["ci"]:
        score += 0.03; reasons.append("Touches CI/workflows (often mergeable if minimal).")
    if buckets["build"]:
        score -= 0.10; reasons.append("Touches dependency/build files (higher review friction).")

    # Repo signals
    if signals.get("ci_detected"):
        score += 0.04; reasons.append("CI detected in repo.")
    else:
        score -= 0.03; reasons.append("No CI detected (harder to verify).")

    if signals.get("contributing_detected"):
        score += 0.02; reasons.append("CONTRIBUTING.md exists (clearer expectations).")

    # PRSpec hints
    if prspec:
        risk = prspec.get("risk")
        if risk == "low":
            score += 0.06; reasons.append("Marked as low risk.")
        elif risk == "high":
            score -= 0.10; reasons.append("Marked as high risk.")

        if prspec.get("breaking_change") is True:
            blockers.append("Breaking change flagged.")
            score -= 0.25

        tp = prspec.get("test_plan") or []
        if isinstance(tp, list) and len(tp) >= 1:
            score += 0.05; reasons.append("Has explicit test plan.")
        else:
            score -= 0.05; reasons.append("Missing explicit test plan.")

        body = prspec.get("body_markdown", "")
        if isinstance(body, str) and ("How tested" in body or "How tested" in body.lower() or "How tested" in body):
            score += 0.02

    # Clamp
    score = max(0.0, min(1.0, score))
    label = "high" if score >= 0.70 else "medium" if score >= 0.45 else "low"
    return {
        "probability": score,
        "label": label,
        "reasons": reasons,
        "blockers": blockers,
        "diff": {"files": diff.files, "insertions": diff.insertions, "deletions": diff.deletions, "paths": diff.paths[:50]},
        "signals": signals,
        "buckets": buckets,
    }


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def allowed_files_from_prspec(prspec: Dict[str, Any]) -> List[str]:
    files = prspec.get("files_touched")
    if not isinstance(files, list):
        return []
    out: List[str] = []
    for item in files:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
    return out


def matches_allowed(path: str, allowed_patterns: List[str]) -> bool:
    normalized = path.replace("\\", "/")
    for pattern in allowed_patterns:
        p = pattern.replace("\\", "/")
        if fnmatch.fnmatch(normalized, p):
            return True
        # Treat literal path entries as "the file or any child under directory-like path".
        if normalized == p or normalized.startswith(f"{p.rstrip('/')}/"):
            return True
    return False


def detect_unplanned_paths(changed_paths: List[str], allowed_patterns: List[str]) -> List[str]:
    if not allowed_patterns:
        return changed_paths[:]
    return sorted([p for p in changed_paths if not matches_allowed(p, allowed_patterns)])


def _run_restore(repo_root: Path, tracked_paths: List[str]) -> Optional[str]:
    if not tracked_paths:
        return None

    restore_cmd = ["git", "restore", "--staged", "--worktree", "--", *tracked_paths]
    p = run(restore_cmd, cwd=repo_root)
    if p.returncode == 0:
        return None

    # Compatibility fallback for older git versions.
    checkout_cmd = ["git", "checkout", "--", *tracked_paths]
    p_checkout = run(checkout_cmd, cwd=repo_root)
    if p_checkout.returncode != 0:
        return p_checkout.stderr.strip() or p.stderr.strip() or "git restore/checkout failed"

    unstage_cmd = ["git", "reset", "HEAD", "--", *tracked_paths]
    p_unstage = run(unstage_cmd, cwd=repo_root)
    if p_unstage.returncode != 0:
        return p_unstage.stderr.strip() or "git reset HEAD failed while unstaging unplanned paths"
    return None


def cleanup_unplanned_paths(repo_root: Path,
                            status_entries: List[StatusEntry],
                            unplanned_paths: List[str]) -> Dict[str, Any]:
    unplanned_set = set(unplanned_paths)
    tracked = sorted([entry.path for entry in status_entries if entry.path in unplanned_set and entry.code != "??"])
    untracked = sorted([entry.path for entry in status_entries if entry.path in unplanned_set and entry.code == "??"])

    cleaned: List[str] = []
    errors: List[str] = []

    tracked_err = _run_restore(repo_root, tracked)
    if tracked_err:
        errors.append(tracked_err)
    else:
        cleaned.extend(tracked)

    if untracked:
        clean_cmd = ["git", "clean", "-fd", "--", *untracked]
        p_clean = run(clean_cmd, cwd=repo_root)
        if p_clean.returncode != 0:
            errors.append(p_clean.stderr.strip() or "git clean failed for untracked unplanned paths")
        else:
            cleaned.extend(untracked)

    return {
        "cleaned": sorted(cleaned),
        "errors": errors,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="PR Factory quality gate: forbidden files + merge probability.")
    ap.add_argument("--repo", required=True, help="Path to repository root")
    ap.add_argument("--prspec", required=False, help="Path to PRSpec JSON (optional)")
    ap.add_argument("--base-ref", default="HEAD", help="Git base ref for diff (default: HEAD)")
    ap.add_argument("--forbidden", nargs="*", default=None, help="Override forbidden globs")
    ap.add_argument("--enforce-files-touched", action="store_true",
                    help="Fail if working-tree changes include files outside PRSpec files_touched.")
    ap.add_argument("--autoclean-unplanned", action="store_true",
                    help="Restore/remove unplanned files outside PRSpec files_touched.")
    ap.add_argument("--json", action="store_true", help="Print JSON report to stdout")
    args = ap.parse_args()

    repo_root = Path(args.repo).resolve()
    if not repo_root.exists():
        raise SystemExit(f"Repo path not found: {repo_root}")

    status_entries = git_status_entries(repo_root)
    changed = sorted({entry.path for entry in status_entries})
    forbidden_hits = scan_forbidden_paths(repo_root, candidate_paths=changed, forbidden_globs=args.forbidden)
    secret_hits = scan_for_secrets(repo_root, candidate_paths=changed)
    diff = git_diff_stats(repo_root, base_ref=args.base_ref)
    signals = repo_signals(repo_root)
    prspec = load_json(Path(args.prspec)) if args.prspec else None

    files_touched_report: Dict[str, Any] = {}
    unplanned_paths: List[str] = []
    if args.enforce_files_touched:
        if not prspec:
            raise SystemExit("--enforce-files-touched requires --prspec")
        allowed_patterns = allowed_files_from_prspec(prspec)
        unplanned_paths = detect_unplanned_paths(changed, allowed_patterns)
        files_touched_report = {
            "enabled": True,
            "allowed_patterns": allowed_patterns,
            "unplanned_paths": unplanned_paths,
            "autoclean_applied": False,
            "autoclean_errors": [],
            "autocleaned_paths": [],
        }

        if args.autoclean_unplanned and unplanned_paths:
            cleanup = cleanup_unplanned_paths(repo_root, status_entries, unplanned_paths)
            files_touched_report["autoclean_applied"] = True
            files_touched_report["autoclean_errors"] = cleanup["errors"]
            files_touched_report["autocleaned_paths"] = cleanup["cleaned"]

            # Recompute state after cleanup.
            status_entries = git_status_entries(repo_root)
            changed = sorted({entry.path for entry in status_entries})
            forbidden_hits = scan_forbidden_paths(repo_root, candidate_paths=changed, forbidden_globs=args.forbidden)
            secret_hits = scan_for_secrets(repo_root, candidate_paths=changed)
            diff = git_diff_stats(repo_root, base_ref=args.base_ref)
            unplanned_paths = detect_unplanned_paths(changed, allowed_patterns)
            files_touched_report["unplanned_paths"] = unplanned_paths

    report = {
        "repo": str(repo_root),
        "changed_paths": changed,
        "forbidden_hits": forbidden_hits,
        "secret_hits": secret_hits,
        "files_touched_check": files_touched_report,
        "merge_assessment": merge_probability(prspec, diff, signals, forbidden_hits, secret_hits),
        "ok": (len(forbidden_hits) == 0 and len(secret_hits) == 0 and len(unplanned_paths) == 0),
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Changed files: {len(changed)}")
        if forbidden_hits:
            print("FORBIDDEN:")
            for p in forbidden_hits:
                print("  -", p)
        if secret_hits:
            print("POTENTIAL SECRETS:")
            for f in secret_hits:
                print(f"  - {f['path']} ({f['snippet']})")
        if args.enforce_files_touched:
            if unplanned_paths:
                print("UNPLANNED PATHS (outside PRSpec files_touched):")
                for p in unplanned_paths:
                    print("  -", p)
            else:
                print("Files-touched check: OK")
            if files_touched_report.get("autoclean_applied"):
                print(f"Autocleaned: {len(files_touched_report.get('autocleaned_paths', []))}")
                for err in files_touched_report.get("autoclean_errors", []):
                    print("AUTOCLEAN ERROR:", err)
        ma = report["merge_assessment"]
        print(f"Merge probability: {ma['probability']:.2f} ({ma['label']})")
        if ma["blockers"]:
            print("Blockers:")
            for b in ma["blockers"]:
                print("  -", b)

    # Exit code for CI
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
