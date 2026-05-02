from pathlib import Path
import shutil
from uuid import uuid4

from bug_fixing_mas.fix_generator_agent.agent_fix_generator import fix_generator_agent
from bug_fixing_mas.tester_agent.agent_tester import tester_agent


TEST_TEMP_ROOT = Path(__file__).resolve().parents[2] / ".tmp_testdata"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


def _make_temp_dir() -> Path:
    path = TEST_TEMP_ROOT / f"case_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_rollback_demo_restores_original_file() -> None:
    temp_root = _make_temp_dir()
    try:
        project = temp_root / "project"
        project.mkdir()
        original_code = (
            "def add(a: float, b: float) -> float:\n"
            "    return a + b\n\n\n"
            "def divide(a: float, b: float) -> float:\n"
            "    if b == 0:\n"
            "        return 0\n"
            "    return a / b\n"
        )
        (project / "calculator.py").write_text(original_code, encoding="utf-8")
        (project / "test_calculator.py").write_text(
            "import pytest\n\nfrom calculator import add, divide\n\n\ndef test_add():\n    assert add(2, 3) == 5\n\n\ndef test_divide():\n    assert divide(10, 2) == 5\n\n\ndef test_divide_by_zero():\n    with pytest.raises(ZeroDivisionError):\n        divide(5, 0)\n",
            encoding="utf-8",
        )

        state = {
            "run_id": "rollback-demo",
            "bug_report": "Rollback demo for validation pipeline. Force a bad patch so rollback can be observed.",
            "project_path": str(project),
            "language": "python",
            "source_extensions": [".py"],
            "test_command": ["python", "-m", "pytest", "-q"],
            "execution_log_path": str(temp_root / "logs" / "rollback.jsonl"),
            "classification": {
                "bug_type": "ArithmeticError",
                "severity": "High",
                "summary": "Calculator should raise ZeroDivisionError for divide by zero.",
                "likely_modules": ["calculator"],
            },
            "root_cause": {
                "suspected_file": "calculator.py",
                "suspected_function": "divide",
                "evidence": ["calculator.py:5 -> return 0"],
                "reasoning": "Divide returns 0 instead of raising.",
            },
            "status": "analyzed",
        }
        patched_state = fix_generator_agent(state)
        tested_state = tester_agent(patched_state)
        assert tested_state["status"] == "rolled_back"
        assert tested_state["test_results"]["restored_original"] is True
        assert Path(patched_state["patch"]["target_file"]).read_text(encoding="utf-8") == original_code
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
