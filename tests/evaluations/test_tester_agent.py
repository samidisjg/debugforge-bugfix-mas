from pathlib import Path
import shutil
from uuid import uuid4

from bug_fixing_mas.tester_agent.agent_tester import tester_agent as run_tester_agent


TEST_TEMP_ROOT = Path(__file__).resolve().parents[2] / ".tmp_testdata"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


def _make_temp_dir() -> Path:
    path = TEST_TEMP_ROOT / f"case_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_tester_writes_final_report() -> None:
    temp_root = _make_temp_dir()
    try:
        project = temp_root / "project"
        project.mkdir()
        (project / "test_dummy.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

        state = {
            "run_id": "tester-demo",
            "bug_report": "Simple validation bug.",
            "project_path": str(project),
            "language": "python",
            "source_extensions": [".py"],
            "test_command": ["python", "-m", "pytest", "-q"],
            "execution_log_path": str(temp_root / "logs" / "tester.jsonl"),
            "classification": {"bug_type": "Validation Bug", "severity": "Low", "summary": "demo", "likely_modules": []},
            "root_cause": {"suspected_file": "dummy.py", "suspected_function": "check", "evidence": ["dummy.py:1 -> demo"], "reasoning": "demo"},
            "patch": {"target_file": "dummy.py", "backup_file": "dummy.py.bak", "change_summary": "demo"},
            "status": "patched",
        }
        updated = run_tester_agent(state)
        assert updated["test_results"]["passed"] is True
        assert Path(updated["final_report_path"]).exists()
        assert "# Bug Fixing MAS Report" in updated["final_report_markdown"]
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
