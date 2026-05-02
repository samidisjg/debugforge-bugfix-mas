from pathlib import Path
import shutil
from uuid import uuid4

from bug_fixing_mas.service import build_initial_state
from bug_fixing_mas.classifier_agent.agent_classifier import classifier_agent


TEST_TEMP_ROOT = Path(__file__).resolve().parents[2] / ".tmp_testdata"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


def _make_temp_dir() -> Path:
    path = TEST_TEMP_ROOT / f"case_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_classifier_flags_concurrency_bug() -> None:
    state = {
        "run_id": "classifier-demo",
        "bug_report": (
            "Race condition in threaded counter update.\n"
            "Multiple threads update shared state without a lock."
        ),
        "project_path": "sample_projects/python_concurrency",
        "language": "python",
        "source_extensions": [".py"],
        "test_command": ["python", "-m", "pytest", "-q"],
        "execution_log_path": "logs/test_classifier.jsonl",
        "status": "received",
    }
    updated = classifier_agent(state)
    assert "concurrency" in updated["classification"]["bug_type"].lower()


def test_classifier_recognizes_validation_bug_context() -> None:
    state = {
        "run_id": "classifier-validation",
        "bug_report": "Negative age input should raise ValueError but currently returns the value.",
        "project_path": "sample_projects/python_validation",
        "language": "python",
        "source_extensions": [".py"],
        "test_command": ["python", "-m", "pytest", "-q"],
        "execution_log_path": "logs/test_classifier.jsonl",
        "status": "received",
    }
    updated = classifier_agent(state)
    assert any(word in updated["classification"]["summary"].lower() for word in ["valueerror", "validation", "negative"])


def test_build_initial_state_sets_language_and_command() -> None:
    temp_root = _make_temp_dir()
    try:
        sample_project = temp_root / "sample_project"
        sample_project.mkdir()
        (sample_project / "calculator.py").write_text("def divide(a, b):\n    return 0\n", encoding="utf-8")
        state = build_initial_state(temp_root, "bug", None, None, None)
        assert state["language"] == "python"
        assert state["test_command"] == ["python", "-m", "pytest", "-q"]
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
