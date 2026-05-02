from pathlib import Path
import shutil
from uuid import uuid4

from bug_fixing_mas.service import DEFAULT_BUGGY_CALCULATOR, build_initial_state


TEST_TEMP_ROOT = Path(__file__).resolve().parents[2] / ".tmp_testdata"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


def _make_temp_dir() -> Path:
    path = TEST_TEMP_ROOT / f"case_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_build_initial_state_resets_demo_project() -> None:
    project_root = _make_temp_dir()
    try:
        sample_project = project_root / "sample_project"
        sample_project.mkdir()
        (sample_project / "calculator.py").write_text("broken\n", encoding="utf-8")

        state = build_initial_state(project_root, "bug", None, None, None)

        assert state["status"] == "received"
        assert state["language"] == "python"
        assert (sample_project / "calculator.py").read_text(encoding="utf-8") == DEFAULT_BUGGY_CALCULATOR
    finally:
        shutil.rmtree(project_root, ignore_errors=True)
