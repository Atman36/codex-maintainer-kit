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

    def get_check(self, result, name):
        return next(check for check in result.checks if check.name == name)

    def write_alias_stage_stub(self):
        stage_stub = self.factory.root / "alias_stage_stub.py"
        stage_stub.write_text(
            textwrap.dedent(
                """
                import json
                import sys
                from pathlib import Path

                TS = "2026-01-01T00:00:00Z"

                def emit(stage, status="success", summary="ok", data=None, pr_spec=None):
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

                def make_pr_spec(candidate_id):
                    return {
                        "schema_version": "1.0",
                        "id": f"prspec-{candidate_id}",
                        "repo": {"url": "https://example.com/repo", "owner": "o", "name": "n", "default_branch": "main"},
                        "base": {"branch": "main"},
                        "head": {"branch": f"feature/{candidate_id}"},
                        "title": f"Alias test {candidate_id}",
                        "body_markdown": "## What\\nAlias test\\n\\n## Why\\nCoverage\\n\\n## How to verify\\n```bash\\npython3 -m unittest tools/tests/test_run_pipeline.py\\n```",
                        "change_type": "test",
                        "risk": "low",
                        "files_touched": ["README.md"],
                        "test_plan": ["python3 -m unittest tools/tests/test_run_pipeline.py"],
                        "ai_assistance": {"used": True, "tools": [{"name": "codex", "role": "test"}], "disclosure_line": "AI assisted"},
                    }

                stage = sys.argv[1]
                if stage == "scout":
                    emit("scout", data={"candidates": [{"id": "cand-scout"}]})
                elif stage == "analyst":
                    source = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
                    emit("analyst", data={"candidates": [{"id": "cand-analyst", "source_stage": source["stage"]}]})
                elif stage == "architect":
                    emit("architect", data={"candidates": [{"id": "cand-architect"}]})
                elif stage == "critic":
                    emit("critic", data={"decision": "approve"})
                elif stage == "gatekeeper":
                    source = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
                    candidate_id = source["data"]["candidates"][0]["id"]
                    pr_spec = make_pr_spec(candidate_id)
                    emit(
                        "gatekeeper",
                        data={
                            "selected": [{"candidate_id": candidate_id, "decision": "pr"}],
                            "pr_specs": [pr_spec],
                            "source_stage": source["stage"],
                        },
                        pr_spec=pr_spec,
                    )
                elif stage == "implement":
                    pr_spec = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
                    emit("implement", data={"implemented": pr_spec["id"]})
                elif stage == "reviewer":
                    implement_result = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
                    emit("reviewer", data={"reviewed": implement_result["data"]["implemented"]})
                elif stage == "pr_writer":
                    pr_spec = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
                    emit("pr_writer", pr_spec=pr_spec)
                else:
                    raise SystemExit(f"unknown stage: {stage}")
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        return stage_stub

    def write_stage_stub(self, name, source):
        stage_stub = self.factory.root / name
        stage_stub.write_text(textwrap.dedent(source).strip() + "\n", encoding="utf-8")
        return stage_stub

    def make_valid_pr_spec(self, spec_id="prspec-1"):
        return {
            "schema_version": "1.0",
            "id": spec_id,
            "repo": {
                "url": "https://example.com/repo",
                "owner": "o",
                "name": "n",
                "default_branch": "main",
            },
            "base": {"branch": "main"},
            "head": {"branch": f"feature/{spec_id}"},
            "title": f"Spec {spec_id} title",
            "body_markdown": "## What\nValid spec\n\n## Why\nValidation coverage\n\n## How to verify\n```bash\necho ok\n```",
            "change_type": "test",
            "risk": "low",
            "files_touched": ["README.md"],
            "test_plan": ["echo ok"],
            "ai_assistance": {
                "used": True,
                "tools": [{"name": "codex", "role": "test"}],
                "disclosure_line": "AI assisted",
            },
        }

    def run_alias_pipeline(self, mode):
        repo = self.factory.create_repo(with_origin=True, push_origin=True, dirty=False)
        stage_stub = self.write_alias_stage_stub()
        py = shlex.quote(str(stage_stub))
        stage_commands = [
            "--stage-command",
            f"implement=python3 {py} implement {{{{PRSPEC_JSON}}}}",
            "--stage-command",
            f"reviewer=python3 {py} reviewer {{{{IMPLEMENT_RESULT_JSON}}}}",
            "--stage-command",
            f"pr_writer=python3 {py} pr_writer {{{{PRSPEC_JSON}}}}",
        ]

        if mode == "quick-win":
            stage_commands = [
                "--stage-command",
                f"scout=python3 {py} scout",
                "--stage-command",
                f"gatekeeper=python3 {py} gatekeeper {{{{CANDIDATES_JSON}}}}",
                *stage_commands,
            ]
        elif mode == "full":
            stage_commands = [
                "--stage-command",
                f"scout=python3 {py} scout",
                "--stage-command",
                f"analyst=python3 {py} analyst {{{{SCOUT_JSON}}}}",
                "--stage-command",
                f"critic=python3 {py} critic",
                "--stage-command",
                f"gatekeeper=python3 {py} gatekeeper {{{{CANDIDATES_JSON}}}}",
                *stage_commands,
            ]
        elif mode == "architecture":
            stage_commands = [
                "--stage-command",
                f"architect=python3 {py} architect",
                "--stage-command",
                f"critic=python3 {py} critic",
                "--stage-command",
                f"gatekeeper=python3 {py} gatekeeper {{{{CANDIDATES_JSON}}}}",
                *stage_commands,
            ]
        else:
            raise ValueError(f"unsupported mode: {mode}")

        args = run_pipeline.parse_args(
            [
                "--repo-root",
                str(repo),
                "--mode",
                mode,
                "--runner",
                "cli",
                *stage_commands,
            ]
        )
        return run_pipeline.run_pipeline(args)

    def run_quick_win_pipeline_with_stub(self, repo, stage_stub):
        py = shlex.quote(str(stage_stub))
        args = run_pipeline.parse_args(
            [
                "--repo-root",
                str(repo),
                "--mode",
                "quick-win",
                "--runner",
                "cli",
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
        return run_pipeline.run_pipeline(args)

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

    def test_preflight_allows_non_publish_without_origin_remote(self):
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
        self.assertTrue(result.passed)
        self.assertEqual(self.get_check(result, "remotes").status, "warn")
        self.assertEqual(self.get_check(result, "base_sha").status, "warn")
        self.assertTrue(any("local-only preflight" in item for item in result.warnings))
        self.assertTrue(any("local base branch 'main'" in item for item in result.warnings))

    def test_preflight_allows_local_base_branch_when_origin_base_missing(self):
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
        self.assertTrue(result.passed)
        base_sha_check = self.get_check(result, "base_sha")
        self.assertEqual(base_sha_check.status, "warn")
        self.assertIn("(main)", base_sha_check.detail)
        self.assertTrue(any("local base branch 'main'" in item for item in result.warnings))

    def test_preflight_allows_head_fallback_for_non_publish(self):
        repo = self.factory.create_repo(with_origin=False, push_origin=False, dirty=False)
        run_cmd(["git", "checkout", "-b", "scratch"], cwd=repo)
        run_cmd(["git", "branch", "-D", "main"], cwd=repo)

        result = run_pipeline.run_preflight(
            repo_root=repo,
            base_branch="main",
            allow_dirty=False,
            publish_requested=False,
            stage_commands={},
            required_stages=[],
            runner_selected="cli",
        )
        self.assertTrue(result.passed)
        base_sha_check = self.get_check(result, "base_sha")
        self.assertEqual(base_sha_check.status, "warn")
        self.assertIn("(HEAD)", base_sha_check.detail)
        self.assertTrue(any("used HEAD" in item for item in result.warnings))

    def test_preflight_publish_requires_origin_remote(self):
        repo = self.factory.create_repo(with_origin=False, push_origin=False, dirty=False)
        result = run_pipeline.run_preflight(
            repo_root=repo,
            base_branch="main",
            allow_dirty=False,
            publish_requested=True,
            stage_commands={},
            required_stages=[],
            runner_selected="cli",
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.checks[-1].name, "remotes")

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

    def test_pipeline_supports_implement_result_alias(self):
        exit_code, payload = self.run_alias_pipeline(mode="quick-win")

        self.assertEqual(exit_code, 0)
        pr_results = payload["data"]["pr_results"]
        self.assertEqual(len(pr_results), 1)
        self.assertEqual(pr_results[0]["status"], "success")
        reviewer_summary = next(
            item for item in pr_results[0]["stage_summary"] if item["stage"] == "reviewer"
        )
        self.assertIn("implement.json", reviewer_summary["command"])

    def test_pipeline_supports_candidates_alias_across_modes(self):
        expected_sources = {
            "quick-win": "scout",
            "full": "analyst",
            "architecture": "architect",
        }

        for mode, expected_source in expected_sources.items():
            with self.subTest(mode=mode):
                exit_code, payload = self.run_alias_pipeline(mode=mode)
                self.assertEqual(exit_code, 0)
                gatekeeper_stage = next(
                    item
                    for item in payload["data"]["stage_summary"]
                    if item["stage"] == "gatekeeper"
                )
                self.assertIn(f"{expected_source}.json", gatekeeper_stage["command"])
                pr_spec = payload["data"]["pr_results"][0]["pr_spec"]
                self.assertEqual(pr_spec["id"], f"prspec-cand-{expected_source}")

    def test_unknown_placeholder_fails_before_stage_execution(self):
        marker = self.factory.root / "unknown-placeholder-ran.txt"
        command = shlex.quote(
            f"from pathlib import Path; Path({str(marker)!r}).write_text('ran', encoding='utf-8')"
        )

        run_result, attempts, retry_trace = run_pipeline.execute_stage_with_retries(
            adapter=run_pipeline.CliRunnerAdapter(),
            stage="reviewer",
            command_template=f"python3 -c {command} {{{{UNKNOWN_JSON}}}}",
            cwd=self.factory.root,
            template_values={},
            max_attempts=1,
        )

        self.assertEqual(attempts, 1)
        self.assertEqual(len(retry_trace), 1)
        self.assertEqual(run_result.exit_code, 1)
        self.assertIn("Unresolved placeholder(s) in stage command", run_result.stderr)
        self.assertFalse(marker.exists())

    def test_invalid_execution_result_rejected_at_stage_boundary(self):
        stage_stub = self.write_stage_stub(
            "invalid_execution_result_stub.py",
            """
            import json

            print(json.dumps({
                "schema_version": "1.0",
                "id": "scout-id",
                "stage": "scout",
                "summary": "missing status",
                "started_at": "2026-01-01T00:00:00Z",
                "finished_at": "2026-01-01T00:00:00Z",
                "exit_code": 0,
                "stdout": "",
                "stderr": "",
                "artifacts": [],
                "metrics": {
                    "duration_ms": 1,
                    "cost_usd": 0.0,
                    "tokens_in": 0,
                    "tokens_out": 0
                },
                "errors": [],
                "warnings": [],
                "data": {}
            }))
            """,
        )

        run_result, attempts, retry_trace = run_pipeline.execute_stage_with_retries(
            adapter=run_pipeline.CliRunnerAdapter(),
            stage="scout",
            command_template=f"python3 {shlex.quote(str(stage_stub))}",
            cwd=self.factory.root,
            template_values={},
            max_attempts=1,
        )

        self.assertEqual(attempts, 1)
        self.assertEqual(len(retry_trace), 1)
        self.assertEqual(run_result.exit_code, 1)
        self.assertIn("ExecutionResult validation", run_result.stderr)
        self.assertIn("field: status", run_result.stderr)
        self.assertIn("schema: required", run_result.stderr)

    def test_invalid_top_level_pr_spec_rejected_before_implement_stage(self):
        repo = self.factory.create_repo(with_origin=True, push_origin=True, dirty=False)
        invalid_spec = self.make_valid_pr_spec("prspec-invalid-top")
        invalid_spec["risk"] = "critical"
        stage_stub = self.write_stage_stub(
            "invalid_top_level_prspec_stub.py",
            f"""
            import json
            import sys

            TS = "2026-01-01T00:00:00Z"
            PR_SPEC = {repr(invalid_spec)}

            def emit(stage, data=None, pr_spec=None):
                payload = {{
                    "schema_version": "1.0",
                    "id": f"{{stage}}-id",
                    "stage": stage,
                    "status": "success",
                    "summary": "ok",
                    "started_at": TS,
                    "finished_at": TS,
                    "exit_code": 0,
                    "stdout": "",
                    "stderr": "",
                    "artifacts": [],
                    "metrics": {{
                        "duration_ms": 1,
                        "cost_usd": 0.0,
                        "tokens_in": 0,
                        "tokens_out": 0,
                    }},
                    "errors": [],
                    "warnings": [],
                    "data": data or {{}},
                }}
                if pr_spec is not None:
                    payload["pr_spec"] = pr_spec
                print(json.dumps(payload))

            stage = sys.argv[1]
            if stage == "scout":
                emit("scout", data={{"candidates": [{{"id": "cand-1"}}]}})
            elif stage == "gatekeeper":
                emit("gatekeeper", data={{"selected": [{{"candidate_id": "cand-1", "decision": "pr"}}]}}, pr_spec=PR_SPEC)
            elif stage == "implement":
                raise SystemExit("implement should not run")
            else:
                emit(stage)
            """,
        )

        exit_code, payload = self.run_quick_win_pipeline_with_stub(repo=repo, stage_stub=stage_stub)

        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["status"], "needs_human")
        self.assertFalse(payload["data"]["pr_results"])
        self.assertIn("Stage 'gatekeeper' output", payload["stderr"])
        self.assertIn("$.pr_spec.risk", payload["stderr"])
        self.assertIn("field: risk", payload["stderr"])

    def test_invalid_data_pr_specs_rejected(self):
        repo = self.factory.create_repo(with_origin=True, push_origin=True, dirty=False)
        invalid_spec = self.make_valid_pr_spec("prspec-invalid-list")
        invalid_spec["risk"] = "critical"
        stage_stub = self.write_stage_stub(
            "invalid_data_prspecs_stub.py",
            f"""
            import json
            import sys

            TS = "2026-01-01T00:00:00Z"
            PR_SPEC = {repr(invalid_spec)}

            def emit(stage, data=None):
                print(json.dumps({{
                    "schema_version": "1.0",
                    "id": f"{{stage}}-id",
                    "stage": stage,
                    "status": "success",
                    "summary": "ok",
                    "started_at": TS,
                    "finished_at": TS,
                    "exit_code": 0,
                    "stdout": "",
                    "stderr": "",
                    "artifacts": [],
                    "metrics": {{
                        "duration_ms": 1,
                        "cost_usd": 0.0,
                        "tokens_in": 0,
                        "tokens_out": 0,
                    }},
                    "errors": [],
                    "warnings": [],
                    "data": data or {{}},
                }}))

            stage = sys.argv[1]
            if stage == "scout":
                emit("scout", data={{"candidates": [{{"id": "cand-1"}}]}})
            elif stage == "gatekeeper":
                emit(
                    "gatekeeper",
                    data={{
                        "selected": [{{"candidate_id": "cand-1", "decision": "pr"}}],
                        "pr_specs": [PR_SPEC],
                    }},
                )
            elif stage == "implement":
                raise SystemExit("implement should not run")
            else:
                emit(stage)
            """,
        )

        exit_code, payload = self.run_quick_win_pipeline_with_stub(repo=repo, stage_stub=stage_stub)

        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["status"], "needs_human")
        self.assertFalse(payload["data"]["pr_results"])
        self.assertIn("Stage 'gatekeeper' output at data.pr_specs[0]", payload["stderr"])
        self.assertIn("$.risk", payload["stderr"])
        self.assertIn("field: risk", payload["stderr"])

    def test_gatekeeper_needs_human_with_prspec_blocks_fanout(self):
        repo = self.factory.create_repo(with_origin=True, push_origin=True, dirty=False)
        valid_spec = self.make_valid_pr_spec("prspec-needs-human")
        stage_stub = self.write_stage_stub(
            "gatekeeper_needs_human_stub.py",
            f"""
            import json
            import sys

            TS = "2026-01-01T00:00:00Z"
            PR_SPEC = {repr(valid_spec)}

            def emit(stage, status="success", data=None, pr_spec=None):
                payload = {{
                    "schema_version": "1.0",
                    "id": f"{{stage}}-id",
                    "stage": stage,
                    "status": status,
                    "summary": "ok",
                    "started_at": TS,
                    "finished_at": TS,
                    "exit_code": 0,
                    "stdout": "",
                    "stderr": "",
                    "artifacts": [],
                    "metrics": {{
                        "duration_ms": 1,
                        "cost_usd": 0.0,
                        "tokens_in": 0,
                        "tokens_out": 0,
                    }},
                    "errors": [],
                    "warnings": [],
                    "data": data or {{}},
                }}
                if pr_spec is not None:
                    payload["pr_spec"] = pr_spec
                print(json.dumps(payload))

            stage = sys.argv[1]
            if stage == "scout":
                emit("scout", data={{"candidates": [{{"id": "cand-1"}}]}})
            elif stage == "gatekeeper":
                emit(
                    "gatekeeper",
                    status="needs_human",
                    data={{
                        "selected": [{{"candidate_id": "cand-1", "decision": "pr"}}],
                        "pr_specs": [PR_SPEC],
                    }},
                    pr_spec=PR_SPEC,
                )
            elif stage == "implement":
                raise SystemExit("implement should not run")
            else:
                emit(stage)
            """,
        )

        exit_code, payload = self.run_quick_win_pipeline_with_stub(repo=repo, stage_stub=stage_stub)

        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["status"], "needs_human")
        self.assertFalse(payload["data"]["pr_results"])
        self.assertIn("Gatekeeper gate failed: status=needs_human", payload["stderr"])

    def test_raw_critic_payload_rejected(self):
        stage_stub = self.write_stage_stub(
            "raw_critic_payload_stub.py",
            """
            import json

            print(json.dumps({"decision": "approve"}))
            """,
        )

        run_result, attempts, retry_trace = run_pipeline.execute_stage_with_retries(
            adapter=run_pipeline.CliRunnerAdapter(),
            stage="critic",
            command_template=f"python3 {shlex.quote(str(stage_stub))}",
            cwd=self.factory.root,
            template_values={},
            max_attempts=1,
        )

        self.assertEqual(attempts, 1)
        self.assertEqual(len(retry_trace), 1)
        self.assertEqual(run_result.exit_code, 1)
        self.assertIn("Stage 'critic' output failed ExecutionResult validation", run_result.stderr)
        self.assertIn("field: decision", run_result.stderr)

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
