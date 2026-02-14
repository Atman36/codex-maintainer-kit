import importlib.util
import json
import shlex
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


def load_run_pipeline_module():
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "tools" / "run_pipeline.py"
    spec = importlib.util.spec_from_file_location("run_pipeline", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load run_pipeline module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


run_pipeline = load_run_pipeline_module()


def run_cmd(args, cwd):
    subprocess.run(args, cwd=str(cwd), check=True, capture_output=True, text=True)


class GitRepoFactory:
    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def cleanup(self):
        self._tmp.cleanup()

    def create_repo(self, with_origin=True, push_origin=True, dirty=False):
        repo = self.root / f"repo-{len(list(self.root.glob('repo-*')))}"
        repo.mkdir(parents=True, exist_ok=True)

        run_cmd(["git", "init", "-b", "main"], cwd=repo)
        run_cmd(["git", "config", "user.email", "test@example.com"], cwd=repo)
        run_cmd(["git", "config", "user.name", "Test User"], cwd=repo)

        (repo / "README.md").write_text("hello\n", encoding="utf-8")
        run_cmd(["git", "add", "README.md"], cwd=repo)
        run_cmd(["git", "commit", "-m", "init"], cwd=repo)

        if with_origin:
            origin = self.root / f"origin-{repo.name}.git"
            run_cmd(["git", "init", "--bare", str(origin)], cwd=self.root)
            run_cmd(["git", "remote", "add", "origin", str(origin)], cwd=repo)
            if push_origin:
                run_cmd(["git", "push", "-u", "origin", "main"], cwd=repo)

        if dirty:
            (repo / "README.md").write_text("dirty\n", encoding="utf-8")

        return repo


class RunPipelineTests(unittest.TestCase):
    def setUp(self):
        self.factory = GitRepoFactory()

    def tearDown(self):
        self.factory.cleanup()

    def test_runner_auto_fallbacks_to_cli(self):
        adapter, warnings = run_pipeline.select_runner(
            mode="auto",
            task_runner_cmd="missing-task-binary --run {{COMMAND}}",
            cwd=Path.cwd(),
        )
        self.assertEqual(adapter.name, "cli")
        self.assertTrue(any("fallback" in item for item in warnings))

    def test_preflight_fails_for_missing_repo(self):
        missing = self.factory.root / "does-not-exist"
        result = run_pipeline.run_preflight(
            repo_root=missing,
            base_branch="main",
            allow_dirty=False,
            publish_requested=False,
            stage_commands={},
            required_stages=[],
            runner_selected="cli",
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.checks[0].name, "repo_root")

    def test_preflight_fails_for_non_git_repo(self):
        path = self.factory.root / "plain-dir"
        path.mkdir(parents=True, exist_ok=True)
        result = run_pipeline.run_preflight(
            repo_root=path,
            base_branch="main",
            allow_dirty=False,
            publish_requested=False,
            stage_commands={},
            required_stages=[],
            runner_selected="cli",
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.checks[-1].name, "git_repo")

    def test_preflight_fails_for_dirty_worktree(self):
        repo = self.factory.create_repo(with_origin=True, push_origin=True, dirty=True)
        result = run_pipeline.run_preflight(
            repo_root=repo,
            base_branch="main",
            allow_dirty=False,
            publish_requested=False,
            stage_commands={},
            required_stages=[],
            runner_selected="cli",
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.checks[-1].name, "dirty_worktree")

    def test_preflight_fails_without_origin_remote(self):
        repo = self.factory.create_repo(with_origin=False, push_origin=False, dirty=False)
        result = run_pipeline.run_preflight(
            repo_root=repo,
            base_branch="main",
            allow_dirty=False,
            publish_requested=False,
            stage_commands={},
            required_stages=[],
            runner_selected="cli",
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.checks[-1].name, "remotes")

    def test_preflight_fails_without_origin_base_sha(self):
        repo = self.factory.create_repo(with_origin=True, push_origin=False, dirty=False)
        result = run_pipeline.run_preflight(
            repo_root=repo,
            base_branch="main",
            allow_dirty=False,
            publish_requested=False,
            stage_commands={},
            required_stages=[],
            runner_selected="cli",
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.checks[-1].name, "base_sha")

    def test_preflight_publish_requires_gh(self):
        repo = self.factory.create_repo(with_origin=True, push_origin=True, dirty=False)
        result = run_pipeline.run_preflight(
            repo_root=repo,
            base_branch="main",
            allow_dirty=False,
            publish_requested=True,
            stage_commands={},
            required_stages=[],
            runner_selected="cli",
            command_exists_fn=lambda binary: False if binary == "gh" else True,
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.checks[-1].name, "publish_tooling")

    def test_multi_pr_partial_failure_keeps_other_results(self):
        repo = self.factory.create_repo(with_origin=True, push_origin=True, dirty=False)
        summary_output = self.factory.root / "pipeline-summary.json"
        stage_stub = self.factory.root / "stage_stub.py"

        stage_stub.write_text(
            textwrap.dedent(
                """
                import json
                import sys
                from pathlib import Path

                TS = "2026-01-01T00:00:00Z"

                def result(stage, status, summary="ok", data=None, pr_spec=None):
                    payload = {
                        "schema_version": "1.0",
                        "id": f"{stage}-id",
                        "stage": stage,
                        "status": status,
                        "summary": summary,
                        "started_at": TS,
                        "finished_at": TS,
                        "exit_code": 0,
                        "stdout": "",
                        "stderr": "",
                        "artifacts": [],
                        "metrics": {
                            "duration_ms": 1,
                            "cost_usd": 0.0,
                            "tokens_in": 0,
                            "tokens_out": 0,
                        },
                        "errors": [],
                        "warnings": [],
                        "data": data or {},
                    }
                    if pr_spec is not None:
                        payload["pr_spec"] = pr_spec
                    print(json.dumps(payload))

                stage = sys.argv[1]
                if stage == "scout":
                    result("scout", "success", data={"candidates": [{"id": "cand-1"}]})
                elif stage == "gatekeeper":
                    pr1 = {
                        "schema_version": "1.0",
                        "id": "prspec-1",
                        "repo": {"url": "https://example.com/repo", "owner": "o", "name": "n", "default_branch": "main"},
                        "base": {"branch": "main"},
                        "head": {"branch": "feature/one"},
                        "title": "Add first test",
                        "body_markdown": "## What\\nFirst\\n\\n## Why\\nFirst\\n\\n## How to verify\\n```bash\\necho one\\n```",
                        "change_type": "test",
                        "risk": "low",
                        "files_touched": ["README.md"],
                        "test_plan": ["echo one"],
                        "ai_assistance": {"used": True, "tools": [{"name": "codex", "role": "test"}], "disclosure_line": "AI assisted"},
                    }
                    pr2 = {
                        "schema_version": "1.0",
                        "id": "prspec-2",
                        "repo": {"url": "https://example.com/repo", "owner": "o", "name": "n", "default_branch": "main"},
                        "base": {"branch": "main"},
                        "head": {"branch": "feature/two"},
                        "title": "Add second test",
                        "body_markdown": "## What\\nSecond\\n\\n## Why\\nSecond\\n\\n## How to verify\\n```bash\\necho two\\n```",
                        "change_type": "test",
                        "risk": "low",
                        "files_touched": ["README.md"],
                        "test_plan": ["echo two"],
                        "ai_assistance": {"used": True, "tools": [{"name": "codex", "role": "test"}], "disclosure_line": "AI assisted"},
                    }
                    result(
                        "gatekeeper",
                        "success",
                        data={
                            "selected": [{"candidate_id": "cand-1", "decision": "pr"}],
                            "pr_specs": [pr1, pr2],
                        },
                        pr_spec=pr1,
                    )
                elif stage == "implement":
                    spec = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
                    if spec.get("id") == "prspec-2":
                        result("implement", "failed", summary="intentional failure")
                    else:
                        result("implement", "success", data={"implemented": spec.get("id")})
                elif stage == "reviewer":
                    result("reviewer", "success")
                elif stage == "pr_writer":
                    spec = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
                    result("pr_writer", "success", pr_spec=spec)
                else:
                    raise SystemExit(f"unknown stage: {stage}")
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )

        py = shlex.quote(str(stage_stub))
        args = run_pipeline.parse_args(
            [
                "--repo-root",
                str(repo),
                "--mode",
                "quick-win",
                "--runner",
                "cli",
                "--max-prs",
                "2",
                "--summary-output",
                str(summary_output),
                "--stage-command",
                f"scout=python3 {py} scout",
                "--stage-command",
                f"gatekeeper=python3 {py} gatekeeper",
                "--stage-command",
                f"implement=python3 {py} implement {{{{PRSPEC_JSON}}}}",
                "--stage-command",
                f"reviewer=python3 {py} reviewer {{{{PRSPEC_JSON}}}}",
                "--stage-command",
                f"pr_writer=python3 {py} pr_writer {{{{PRSPEC_JSON}}}}",
            ]
        )

        exit_code, payload = run_pipeline.run_pipeline(args)
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["status"], "needs_human")
        pr_results = payload["data"]["pr_results"]
        self.assertEqual(len(pr_results), 2)
        self.assertEqual(pr_results[0]["status"], "success")
        self.assertEqual(pr_results[1]["status"], "needs_human")
        self.assertTrue(pr_results[0]["pr_spec"]["head"]["branch"].startswith("codex/"))
        self.assertTrue(summary_output.exists())
        summary_payload = json.loads(summary_output.read_text(encoding="utf-8"))
        self.assertIn("runner_selected", summary_payload)
        self.assertIn("pr_results", summary_payload)

        if importlib.util.find_spec("jsonschema") is not None:
            import jsonschema  # type: ignore

            schema_path = Path(__file__).resolve().parents[2] / "schemas" / "pipeline_summary.schema.json"
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            jsonschema.validate(instance=summary_payload, schema=schema)


if __name__ == "__main__":
    unittest.main()
