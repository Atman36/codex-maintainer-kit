from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence


@dataclass(frozen=True)
class StatusEntry:
    code: str
    path: str


def run_git(args: Sequence[str], cwd: Path, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=check,
    )


def is_git_repo(repo_root: Path) -> bool:
    probe = run_git(["rev-parse", "--is-inside-work-tree"], cwd=repo_root)
    return probe.returncode == 0


def git_status_entries(repo_root: Path) -> List[StatusEntry]:
    """
    Returns modified/added/untracked paths with porcelain status code.
    """
    if not is_git_repo(repo_root):
        return []
    p = run_git(["status", "--porcelain"], cwd=repo_root)
    entries: List[StatusEntry] = []
    for line in p.stdout.splitlines():
        if not line.strip():
            continue
        # Format: XY <path> or XY <path> -> <path>
        # e.g. "?? foo.txt", " M src/a.py", "R  old -> new"
        code = line[:2]
        parts = line[3:].split("->")
        path = parts[-1].strip()
        if path:
            entries.append(StatusEntry(code=code, path=path))
    return entries


def git_status_paths(repo_root: Path) -> List[str]:
    return sorted({entry.path for entry in git_status_entries(repo_root)})

