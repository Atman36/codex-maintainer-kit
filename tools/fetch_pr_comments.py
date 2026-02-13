#!/usr/bin/env python3
"""
Fetch PR comments from GitHub repository.

Supports two types of comments:
- Issue comments: general discussion on PRs
- Review comments: line-specific code review comments

Can use GitHub CLI (gh) if available, or PyGithub as fallback.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import urlencode


def parse_iso_datetime(value: str) -> datetime:
    """Parse ISO datetime and normalize to timezone-aware UTC."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


@dataclass
class Comment:
    """Represents a PR comment."""
    pr_number: int
    pr_title: str
    comment_id: int
    author: str
    body: str
    created_at: str
    updated_at: str
    comment_type: str  # 'issue_comment' or 'review_comment'
    # Review comment specific fields
    commit_id: Optional[str] = None
    path: Optional[str] = None
    line: Optional[int] = None
    diff_hunk: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class GitHubCLIClient:
    """Client using GitHub CLI (gh)."""
    
    def __init__(self, repo: str):
        self.repo = repo
        self._check_cli()
    
    def _check_cli(self) -> None:
        """Verify gh CLI is installed and authenticated."""
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                check=True
            )
        except FileNotFoundError:
            raise RuntimeError(
                "GitHub CLI (gh) not found. Install from https://cli.github.com/"
            )
        except subprocess.CalledProcessError:
            raise RuntimeError(
                "GitHub CLI not authenticated. Run: gh auth login"
            )
    
    @staticmethod
    def _with_query(path: str, **params: Any) -> str:
        """Append URL query parameters to API path."""
        query_params = {k: v for k, v in params.items() if v is not None}
        if not query_params:
            return path
        return f"{path}?{urlencode(query_params)}"

    @staticmethod
    def _parse_json_stream(output: str) -> List[Dict[str, Any]]:
        """Parse gh output that may contain a stream of JSON arrays/objects."""
        output = output.strip()
        if not output:
            return []

        try:
            parsed = json.loads(output)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                return [parsed]
            return []
        except json.JSONDecodeError:
            pass

        decoder = json.JSONDecoder()
        idx = 0
        items: List[Dict[str, Any]] = []
        while idx < len(output):
            while idx < len(output) and output[idx].isspace():
                idx += 1
            if idx >= len(output):
                break

            obj, end_idx = decoder.raw_decode(output, idx)
            if isinstance(obj, list):
                items.extend(obj)
            elif isinstance(obj, dict):
                items.append(obj)
            idx = end_idx
        return items

    def _api_call(
        self,
        endpoint: str,
        paginate: bool = True,
        max_retries: int = 3,
    ) -> List[Dict[str, Any]]:
        """Make API call via gh with retry/backoff for transient errors."""
        cmd = ["gh", "api", f"repos/{self.repo}/{endpoint}"]
        if paginate:
            cmd.append("--paginate")

        last_error: Optional[str] = None
        for attempt in range(max_retries + 1):
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return self._parse_json_stream(result.stdout)

            stderr = (result.stderr or "").strip()
            lower_stderr = stderr.lower()
            retryable = any(
                token in lower_stderr
                for token in (
                    "secondary rate limit",
                    "api rate limit exceeded",
                    "timeout",
                    "timed out",
                    "connection reset",
                    "502",
                    "503",
                    "504",
                )
            )
            last_error = stderr or f"gh exited with code {result.returncode}"

            if attempt < max_retries and retryable:
                delay = min(30, 2 ** attempt)
                print(
                    f"Retrying API call after transient error ({delay}s): {endpoint}",
                    file=sys.stderr,
                )
                time.sleep(delay)
                continue

            break

        raise RuntimeError(f"API call failed for '{endpoint}': {last_error}")
    
    def _fetch_prs_limited(self, max_prs: Optional[int] = None) -> List[Dict[str, Any]]:
        """Fetch PRs with optional limit (avoids full pagination for large repos)."""
        if max_prs is None:
            endpoint = self._with_query("pulls", state="all", per_page=100)
            return self._api_call(endpoint, paginate=True)

        per_page = 100
        pages_needed = (max_prs + per_page - 1) // per_page

        all_prs = []
        for page in range(1, pages_needed + 1):
            endpoint = self._with_query(
                "pulls",
                state="all",
                per_page=per_page,
                page=page,
            )
            prs = self._api_call(endpoint, paginate=False)
            all_prs.extend(prs)
            if len(prs) < per_page or len(all_prs) >= max_prs:
                break

        return all_prs[:max_prs]

    @staticmethod
    def _to_utc_iso8601(dt: datetime) -> str:
        """Convert datetime to GitHub-friendly UTC ISO8601 format."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _parse_dt(value: str) -> datetime:
        return parse_iso_datetime(value)

    def _fetch_comments_parallel(
        self,
        prs: List[Dict[str, Any]],
        comment_kind: str,
        build_endpoint: Any,
        parse_comment: Any,
        max_workers: int,
        strict_errors: bool,
    ) -> Iterator[Comment]:
        if not prs:
            return

        workers = max(1, min(max_workers, len(prs)))
        print(
            f"Fetching {comment_kind} for {len(prs)} PRs with {workers} workers...",
            file=sys.stderr,
        )

        failures: List[str] = []
        completed = 0

        def fetch_one(pr: Dict[str, Any]) -> List[Comment]:
            endpoint = build_endpoint(pr["number"])
            raw_comments = self._api_call(endpoint, paginate=True)
            return [parse_comment(pr, c) for c in raw_comments]

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            future_map = {executor.submit(fetch_one, pr): pr for pr in prs}
            for future in concurrent.futures.as_completed(future_map):
                pr = future_map[future]
                completed += 1

                if completed % 10 == 0 or completed == len(prs):
                    print(
                        f"[{comment_kind}] processed {completed}/{len(prs)} PRs",
                        file=sys.stderr,
                    )

                try:
                    comments = future.result()
                except Exception as exc:
                    failures.append(f"PR #{pr['number']}: {exc}")
                    continue

                for comment in comments:
                    yield comment

        if failures:
            print(
                f"{comment_kind}: failed to fetch {len(failures)} PR(s).",
                file=sys.stderr,
            )
            for failure in failures[:10]:
                print(f"  - {failure}", file=sys.stderr)
            if len(failures) > 10:
                print(
                    f"  ... and {len(failures) - 10} more failures.",
                    file=sys.stderr,
                )
            if strict_errors:
                raise RuntimeError(
                    f"{comment_kind}: failed requests for {len(failures)} PR(s)."
                )

    def fetch_issue_comments(
        self,
        max_prs: Optional[int] = None,
        since: Optional[datetime] = None,
        max_workers: int = 8,
        strict_errors: bool = False,
    ) -> Iterator[Comment]:
        """Fetch issue comments (PR discussions), concurrently per PR."""
        print(f"Fetching issue comments from {self.repo}...", file=sys.stderr)
        prs = self._fetch_prs_limited(max_prs)
        since_value = self._to_utc_iso8601(since) if since else None

        def build_endpoint(pr_number: int) -> str:
            return self._with_query(
                f"issues/{pr_number}/comments",
                per_page=100,
                since=since_value,
            )

        def parse_comment(pr: Dict[str, Any], raw: Dict[str, Any]) -> Comment:
            return Comment(
                pr_number=pr["number"],
                pr_title=pr["title"],
                comment_id=raw["id"],
                author=(raw.get("user") or {}).get("login", "ghost"),
                body=raw.get("body") or "",
                created_at=raw.get("created_at") or "",
                updated_at=raw.get("updated_at") or "",
                comment_type="issue_comment",
            )

        for comment in self._fetch_comments_parallel(
            prs=prs,
            comment_kind="issue comments",
            build_endpoint=build_endpoint,
            parse_comment=parse_comment,
            max_workers=max_workers,
            strict_errors=strict_errors,
        ):
            if since and comment.created_at and self._parse_dt(comment.created_at) < since:
                continue
            yield comment

    def fetch_review_comments(
        self,
        max_prs: Optional[int] = None,
        since: Optional[datetime] = None,
        max_workers: int = 8,
        strict_errors: bool = False,
    ) -> Iterator[Comment]:
        """Fetch review comments, concurrently per PR."""
        print(f"Fetching review comments from {self.repo}...", file=sys.stderr)
        prs = self._fetch_prs_limited(max_prs)
        since_value = self._to_utc_iso8601(since) if since else None

        def build_endpoint(pr_number: int) -> str:
            return self._with_query(
                f"pulls/{pr_number}/comments",
                per_page=100,
                since=since_value,
            )

        def parse_comment(pr: Dict[str, Any], raw: Dict[str, Any]) -> Comment:
            return Comment(
                pr_number=pr["number"],
                pr_title=pr["title"],
                comment_id=raw["id"],
                author=(raw.get("user") or {}).get("login", "ghost"),
                body=raw.get("body") or "",
                created_at=raw.get("created_at") or "",
                updated_at=raw.get("updated_at") or "",
                comment_type="review_comment",
                commit_id=raw.get("commit_id"),
                path=raw.get("path"),
                line=raw.get("line"),
                diff_hunk=raw.get("diff_hunk"),
            )

        for comment in self._fetch_comments_parallel(
            prs=prs,
            comment_kind="review comments",
            build_endpoint=build_endpoint,
            parse_comment=parse_comment,
            max_workers=max_workers,
            strict_errors=strict_errors,
        ):
            if since and comment.created_at and self._parse_dt(comment.created_at) < since:
                continue
            yield comment


class PyGithubClient:
    """Client using PyGithub library."""
    
    def __init__(self, repo: str, token: Optional[str] = None):
        try:
            from github import Github
        except ImportError:
            raise RuntimeError(
                "PyGithub not installed. Install with: pip install PyGithub"
            )
        
        self.repo_name = repo
        self.token = token or os.environ.get("GITHUB_TOKEN")
        if not self.token:
            raise RuntimeError(
                "GitHub token required. Set GITHUB_TOKEN environment variable or use --token"
            )
        
        self.github = Github(self.token)
        self.repo = self.github.get_repo(repo)
        self._pull_cache: Dict[Optional[int], List[Any]] = {}

    @staticmethod
    def _parse_dt(value: str) -> datetime:
        return parse_iso_datetime(value)

    def _get_pulls(self, max_prs: Optional[int]) -> List[Any]:
        if max_prs in self._pull_cache:
            return self._pull_cache[max_prs]

        pulls = self.repo.get_pulls(state="all")
        result: List[Any] = []
        for idx, pull in enumerate(pulls):
            if max_prs is not None and idx >= max_prs:
                break
            result.append(pull)

        self._pull_cache[max_prs] = result
        return result

    def fetch_issue_comments(
        self,
        max_prs: Optional[int] = None,
        since: Optional[datetime] = None,
        max_workers: int = 8,
        strict_errors: bool = False,
    ) -> Iterator[Comment]:
        """Fetch all issue comments (PR discussions)."""
        del max_workers, strict_errors
        print(f"Fetching issue comments from {self.repo_name}...", file=sys.stderr)

        pulls = self._get_pulls(max_prs)
        for pr in pulls:
            try:
                comments = pr.get_issue_comments(since=since) if since else pr.get_issue_comments()
            except TypeError:
                comments = pr.get_issue_comments()

            for comment in comments:
                created_at = comment.created_at.isoformat() if comment.created_at else ""
                if since and created_at and self._parse_dt(created_at) < since:
                    continue
                yield Comment(
                    pr_number=pr.number,
                    pr_title=pr.title,
                    comment_id=comment.id,
                    author=comment.user.login if comment.user else "ghost",
                    body=comment.body,
                    created_at=created_at,
                    updated_at=comment.updated_at.isoformat() if comment.updated_at else "",
                    comment_type="issue_comment",
                )

    def fetch_review_comments(
        self,
        max_prs: Optional[int] = None,
        since: Optional[datetime] = None,
        max_workers: int = 8,
        strict_errors: bool = False,
    ) -> Iterator[Comment]:
        """Fetch all review comments (code review comments on lines)."""
        del max_workers, strict_errors
        print(f"Fetching review comments from {self.repo_name}...", file=sys.stderr)

        pulls = self._get_pulls(max_prs)
        for pr in pulls:
            try:
                comments = pr.get_review_comments(since=since) if since else pr.get_review_comments()
            except TypeError:
                comments = pr.get_review_comments()

            for comment in comments:
                created_at = comment.created_at.isoformat() if comment.created_at else ""
                if since and created_at and self._parse_dt(created_at) < since:
                    continue

                yield Comment(
                    pr_number=pr.number,
                    pr_title=pr.title,
                    comment_id=comment.id,
                    author=comment.user.login if comment.user else "ghost",
                    body=comment.body,
                    created_at=created_at,
                    updated_at=comment.updated_at.isoformat() if comment.updated_at else "",
                    comment_type="review_comment",
                    commit_id=comment.commit_id,
                    path=comment.path,
                    line=comment.line,
                    diff_hunk=comment.diff_hunk,
                )


def create_client(repo: str, token: Optional[str] = None, prefer_cli: bool = True) -> GitHubCLIClient | PyGithubClient:
    """Create appropriate client based on availability."""
    if prefer_cli:
        try:
            return GitHubCLIClient(repo)
        except RuntimeError as e:
            print(f"GitHub CLI not available: {e}", file=sys.stderr)
            print("Falling back to PyGithub...", file=sys.stderr)
    
    return PyGithubClient(repo, token)


def write_json(comments: List[Comment], output: Path) -> None:
    """Write comments to JSON file."""
    data = {
        "meta": {
            "exported_at": datetime.now().isoformat(),
            "total_comments": len(comments),
            "by_type": {}
        },
        "comments": [c.to_dict() for c in comments]
    }
    
    # Count by type
    for c in comments:
        data["meta"]["by_type"][c.comment_type] = data["meta"]["by_type"].get(c.comment_type, 0) + 1
    
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Written {len(comments)} comments to {output}", file=sys.stderr)


def write_csv(comments: List[Comment], output: Path) -> None:
    """Write comments to CSV file."""
    if not comments:
        print("No comments to write", file=sys.stderr)
        return
    
    fieldnames = [
        "pr_number", "pr_title", "comment_id", "author", "body",
        "created_at", "updated_at", "comment_type",
        "commit_id", "path", "line"
    ]
    
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for c in comments:
            row = {
                "pr_number": c.pr_number,
                "pr_title": c.pr_title,
                "comment_id": c.comment_id,
                "author": c.author,
                "body": c.body,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
                "comment_type": c.comment_type,
                "commit_id": c.commit_id or "",
                "path": c.path or "",
                "line": c.line or ""
            }
            writer.writerow(row)
    
    print(f"Written {len(comments)} comments to {output}", file=sys.stderr)


def load_since_from_state(state_file: Path) -> Optional[datetime]:
    """Load last known sync point from state file, if present."""
    if not state_file.exists():
        return None

    try:
        raw = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(raw, dict):
        return None

    last = raw.get("last_comment_created_at") or raw.get("last_sync_at")
    if not isinstance(last, str) or not last.strip():
        return None

    try:
        return parse_iso_datetime(last)
    except ValueError:
        return None


def save_state(state_file: Path, comments: List[Comment]) -> None:
    """Persist sync metadata for future incremental runs."""
    now = datetime.now(timezone.utc)
    max_comment_time: Optional[datetime] = None

    for comment in comments:
        if not comment.created_at:
            continue
        try:
            comment_dt = parse_iso_datetime(comment.created_at)
        except ValueError:
            continue
        if max_comment_time is None or comment_dt > max_comment_time:
            max_comment_time = comment_dt

    payload = {
        "last_sync_at": now.isoformat(),
        "last_comment_created_at": max_comment_time.isoformat() if max_comment_time else now.isoformat(),
        "total_comments_last_run": len(comments),
    }
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch PR comments from GitHub repository"
    )
    parser.add_argument(
        "repo",
        help="Repository in format owner/repo"
    )
    parser.add_argument(
        "--type",
        choices=["issue", "review", "all"],
        default="all",
        help="Type of comments to fetch (default: all)"
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        required=True,
        help="Output file path"
    )
    parser.add_argument(
        "--token",
        help="GitHub token (or set GITHUB_TOKEN env var)"
    )
    parser.add_argument(
        "--prefer-pygithub",
        action="store_true",
        help="Prefer PyGithub over GitHub CLI"
    )
    parser.add_argument(
        "--authors",
        help="Filter by authors (comma-separated)"
    )
    parser.add_argument(
        "--since",
        help="Only comments since date (ISO format)"
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        help="Optional state file for incremental runs (stores last sync point)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Parallel workers for per-PR fetches (default: 8)"
    )
    parser.add_argument(
        "--strict-errors",
        action="store_true",
        help="Fail the run if any PR comment request fails"
    )
    parser.add_argument(
        "--max-prs",
        type=int,
        default=None,
        help="Limit number of PRs to fetch (for quick testing)"
    )
    
    args = parser.parse_args()
    
    # Validate repo format
    if "/" not in args.repo:
        print("Error: Repository must be in format 'owner/repo'", file=sys.stderr)
        return 1

    if args.max_prs is not None and args.max_prs <= 0:
        print("Error: --max-prs must be > 0", file=sys.stderr)
        return 1

    if args.workers <= 0:
        print("Error: --workers must be > 0", file=sys.stderr)
        return 1

    since_dt: Optional[datetime] = None
    if args.since:
        try:
            parsed = datetime.fromisoformat(args.since.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            since_dt = parsed
        except ValueError:
            print(
                "Error: Invalid --since date format. Use ISO format (e.g., 2024-01-01)",
                file=sys.stderr,
            )
            return 1
    elif args.state_file:
        state_since = load_since_from_state(args.state_file)
        if state_since:
            since_dt = state_since
            print(
                f"Using incremental sync point from state: {since_dt.isoformat()}",
                file=sys.stderr,
            )
    
    # Create client
    try:
        client = create_client(
            args.repo,
            args.token,
            prefer_cli=not args.prefer_pygithub
        )
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    
    # Fetch comments
    comments: List[Comment] = []
    
    try:
        if args.type in ("issue", "all"):
            comments.extend(
                client.fetch_issue_comments(
                    max_prs=args.max_prs,
                    since=since_dt,
                    max_workers=args.workers,
                    strict_errors=args.strict_errors,
                )
            )

        if args.type in ("review", "all"):
            comments.extend(
                client.fetch_review_comments(
                    max_prs=args.max_prs,
                    since=since_dt,
                    max_workers=args.workers,
                    strict_errors=args.strict_errors,
                )
            )
    except Exception as e:
        print(f"Error fetching comments: {e}", file=sys.stderr)
        return 1
    
    # Apply filters
    if args.authors:
        authors = set(a.strip().lower() for a in args.authors.split(","))
        comments = [c for c in comments if c.author.lower() in authors]
    
    if since_dt:
        comments = [
            c for c in comments
            if c.created_at and parse_iso_datetime(c.created_at) >= since_dt
        ]

    # Sort by date
    comments.sort(
        key=lambda c: parse_iso_datetime(c.created_at)
        if c.created_at
        else datetime.min.replace(tzinfo=timezone.utc)
    )
    
    # Write output
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    if args.format == "json":
        write_json(comments, args.output)
    else:
        write_csv(comments, args.output)

    if args.state_file:
        save_state(args.state_file, comments)
        print(f"State saved to {args.state_file}", file=sys.stderr)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
