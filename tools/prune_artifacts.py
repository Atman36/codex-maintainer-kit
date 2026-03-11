#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RunArtifact:
    run_id: str
    path: Path
    summary_path: Path
    mtime_epoch: float


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _pipeline_summary_path(artifact_dir: Path, run_id: str) -> Path:
    return artifact_dir / f"pipeline-summary-pipeline-{run_id}.json"


def discover_runs(artifact_dir: Path) -> List[RunArtifact]:
    runs_dir = artifact_dir / "runs"
    if not runs_dir.exists():
        return []

    artifacts: List[RunArtifact] = []
    for child in runs_dir.iterdir():
        if not child.is_dir():
            continue
        stat = child.stat()
        artifacts.append(
            RunArtifact(
                run_id=child.name,
                path=child,
                summary_path=_pipeline_summary_path(artifact_dir, child.name),
                mtime_epoch=stat.st_mtime,
            )
        )
    return sorted(artifacts, key=lambda item: (-item.mtime_epoch, item.run_id))


def select_runs_to_prune(
    runs: List[RunArtifact],
    *,
    keep_last: int,
    max_age_days: Optional[int],
    now: Optional[dt.datetime] = None,
) -> List[RunArtifact]:
    if keep_last < 0:
        raise ValueError("keep_last must be >= 0")
    if max_age_days is not None and max_age_days < 0:
        raise ValueError("max_age_days must be >= 0")

    now = now or _utc_now()
    deletable: List[RunArtifact] = []
    protected_ids = {item.run_id for item in runs[:keep_last]}

    for item in runs:
        if item.run_id in protected_ids:
            continue
        if max_age_days is None:
            deletable.append(item)
            continue

        age = now - dt.datetime.fromtimestamp(item.mtime_epoch, tz=dt.timezone.utc)
        if age >= dt.timedelta(days=max_age_days):
            deletable.append(item)
    return deletable


def prune_runs(
    artifact_dir: Path,
    *,
    keep_last: int = 10,
    max_age_days: Optional[int] = 30,
    dry_run: bool = False,
    now: Optional[dt.datetime] = None,
) -> Dict[str, Any]:
    artifact_dir = artifact_dir.resolve()
    runs = discover_runs(artifact_dir)
    selected = select_runs_to_prune(runs, keep_last=keep_last, max_age_days=max_age_days, now=now)
    selected_ids = {item.run_id for item in selected}

    deleted: List[str] = []
    summary_deleted: List[str] = []
    errors: List[str] = []
    kept = [item.run_id for item in runs if item.run_id not in selected_ids]

    for item in selected:
        if dry_run:
            continue
        try:
            shutil.rmtree(item.path)
            deleted.append(item.run_id)
        except OSError as exc:
            errors.append(f"{item.run_id}: failed to delete run dir: {exc}")
            continue

        if item.summary_path.exists():
            try:
                item.summary_path.unlink()
                summary_deleted.append(str(item.summary_path))
            except OSError as exc:
                errors.append(f"{item.run_id}: failed to delete summary: {exc}")

    return {
        "artifact_dir": str(artifact_dir),
        "runs_total": len(runs),
        "keep_last": keep_last,
        "max_age_days": max_age_days,
        "dry_run": dry_run,
        "deleted_run_ids": [item.run_id for item in selected] if dry_run else deleted,
        "kept_run_ids": kept,
        "summary_files_deleted": summary_deleted,
        "errors": errors,
        "ok": not errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prune old PR Factory run artifacts by run_id retention policy.")
    parser.add_argument("--artifact-dir", required=True, help="Path to analysis_report directory.")
    parser.add_argument("--keep-last", type=int, default=10, help="Always keep this many newest runs.")
    parser.add_argument("--max-age-days", type=int, default=30, help="Delete runs older than this age.")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be deleted without removing files.")
    parser.add_argument("--json", action="store_true", help="Print JSON report.")
    args = parser.parse_args()

    report = prune_runs(
        Path(args.artifact_dir),
        keep_last=args.keep_last,
        max_age_days=args.max_age_days,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"Artifact dir: {report['artifact_dir']}")
        print(f"Runs total: {report['runs_total']}")
        print(f"Deleted runs: {len(report['deleted_run_ids'])}")
        for run_id in report["deleted_run_ids"]:
            print(f"  - {run_id}")
        if report["errors"]:
            print("Errors:")
            for item in report["errors"]:
                print(f"  - {item}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
