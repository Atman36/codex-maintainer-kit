import importlib.util
import io
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


def load_archive_module():
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "tools" / "make_agent_audit_archive.py"
    spec = importlib.util.spec_from_file_location("make_agent_audit_archive", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load make_agent_audit_archive module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


archive_tool = load_archive_module()


def run_cmd(args, cwd):
    subprocess.run(args, cwd=str(cwd), check=True, capture_output=True, text=True)


class MakeAgentAuditArchiveTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir(parents=True, exist_ok=True)
        run_cmd(["git", "init", "-b", "main"], cwd=self.repo)
        run_cmd(["git", "config", "user.email", "test@example.com"], cwd=self.repo)
        run_cmd(["git", "config", "user.name", "Test User"], cwd=self.repo)

    def tearDown(self):
        self._tmp.cleanup()

    def write_file(self, relative_path: str, content: str) -> None:
        path = self.repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def commit_all(self) -> None:
        run_cmd(["git", "add", "."], cwd=self.repo)
        run_cmd(["git", "commit", "-m", "snapshot"], cwd=self.repo)

    def archive_members(self, archive_path: Path) -> list[str]:
        with tarfile.open(archive_path, "r:gz") as handle:
            return sorted(member.name for member in handle.getmembers() if member.isfile())

    def test_create_archive_excludes_noise_paths(self):
        self.write_file("README.md", "ok\n")
        self.write_file("prompts/user-framework-audit.md", "prompt\n")
        self.write_file(".DS_Store", "junk\n")
        self.write_file("analysis_report/run.json", "{}\n")
        self.write_file("artifacts/log.txt", "ignore\n")
        self.write_file("tools/__pycache__/cache.pyc", "x\n")
        self.commit_all()

        archive_path = self.root / "bundle.tar.gz"
        included = archive_tool.create_archive(
            repo_root=self.repo,
            ref="HEAD",
            output_path=archive_path,
            prefix="repo/",
            excludes=archive_tool.DEFAULT_EXCLUDES,
        )

        self.assertEqual(included, ["README.md", "prompts/user-framework-audit.md"])
        self.assertEqual(
            self.archive_members(archive_path),
            ["repo/README.md", "repo/prompts/user-framework-audit.md"],
        )


if __name__ == "__main__":
    unittest.main()
