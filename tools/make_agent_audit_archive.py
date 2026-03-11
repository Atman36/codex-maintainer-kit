#!/usr/bin/env python3
"""
Create a clean source archive for external AI-agent audits.

The archive is built from a committed git ref so local junk and uncommitted
workspace noise are excluded by default.
"""
from __future__ import annotations

import argparse
import fnmatch
import io
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from pr_factory_lib.git_utils import run_git


DEFAULT_EXCLUDES = (
    ".DS_Store",
    ".git/**",
    ".claude/**",
    "analysis_report/**",
    "artifacts/**",
    "deepresearch/**",
    "docx/**",
    "**/__pycache__/**",
    "**/*.pyc",
    "**/*.pyo",
    "**/*.tar.gz",
    "**/*.tgz",
    "**/*.zip",
)


@dataclass(frozen=True)
class GitBlob:
    mode: int
    object_id: str
    path: str


def repo_root_from_tool() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    repo_root = repo_root_from_tool()
    default_output = repo_root.parent / f"{repo_root.name}-agent-audit-archive.tar.gz"

    parser = argparse.ArgumentParser(description="Create a clean AI-audit archive from a git ref.")
    parser.add_argument("--repo", type=Path, default=repo_root, help="Repository root (default: current toolkit repo).")
    parser.add_argument("--ref", default="HEAD", help="Git ref to archive from (default: HEAD).")
    parser.add_argument(
        "--output",
        type=Path,
        default=default_output,
        help=f"Output archive path (default: {default_output}).",
    )
    parser.add_argument(
        "--prefix",
        default="",
        help="Top-level directory prefix inside archive (default: '<repo-name>/'). Use '.' for no prefix.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Additional glob to exclude. May be passed multiple times.",
    )
    return parser.parse_args()


def normalize_prefix(repo_root: Path, prefix_arg: str) -> str:
    if prefix_arg == ".":
        return ""
    if prefix_arg:
        return prefix_arg.rstrip("/") + "/"
    return f"{repo_root.name}/"


def git_blobs(repo_root: Path, ref: str) -> List[GitBlob]:
    proc = run_git(["ls-tree", "-r", "-z", ref], cwd=repo_root)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git ls-tree failed for ref '{ref}'")

    blobs: List[GitBlob] = []
    for record in proc.stdout.split("\0"):
        if not record:
            continue
        meta, path = record.split("\t", 1)
        mode_text, object_type, object_id = meta.split(" ", 2)
        if object_type != "blob":
            continue
        blobs.append(GitBlob(mode=int(mode_text, 8), object_id=object_id, path=path))
    return blobs


def should_exclude(path: str, patterns: Iterable[str]) -> bool:
    normalized = path.replace("\\", "/")
    for pattern in patterns:
        if fnmatch.fnmatch(normalized, pattern):
            return True
    return False


def read_blob(repo_root: Path, object_id: str) -> bytes:
    proc = subprocess.run(
        ["git", "cat-file", "-p", object_id],
        cwd=str(repo_root),
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or f"git cat-file failed for object '{object_id}'")
    return proc.stdout


def create_archive(repo_root: Path, ref: str, output_path: Path, prefix: str, excludes: Iterable[str]) -> List[str]:
    blobs = git_blobs(repo_root=repo_root, ref=ref)
    included_paths: List[str] = []
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tarfile.open(output_path, "w:gz") as archive:
        for blob in blobs:
            if should_exclude(blob.path, excludes):
                continue

            data = read_blob(repo_root=repo_root, object_id=blob.object_id)
            tar_info = tarfile.TarInfo(name=f"{prefix}{blob.path}")
            tar_info.size = len(data)
            tar_info.mode = blob.mode
            archive.addfile(tar_info, io.BytesIO(data))
            included_paths.append(blob.path)

    return included_paths


def main() -> int:
    args = parse_args()
    repo_root = args.repo.resolve()
    output_path = args.output.resolve()
    excludes = [*DEFAULT_EXCLUDES, *args.exclude]
    prefix = normalize_prefix(repo_root=repo_root, prefix_arg=args.prefix)

    included_paths = create_archive(
        repo_root=repo_root,
        ref=args.ref,
        output_path=output_path,
        prefix=prefix,
        excludes=excludes,
    )

    print(f"Archive: {output_path}")
    print(f"Ref: {args.ref}")
    print(f"Files: {len(included_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
