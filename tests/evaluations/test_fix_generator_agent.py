from pathlib import Path
import shutil
from uuid import uuid4

from bug_fixing_mas.fix_generator_agent.agent_fix_generator import fix_generator_agent


TEST_TEMP_ROOT = Path(__file__).resolve().parents[2] / ".tmp_testdata"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)

BUGGY_COUNTER = """import threading
import time


class Counter:
    def __init__(self) -> None:
        self.value = 0

    def increment(self) -> None:
        current = self.value
        time.sleep(0.0001)
        self.value = current + 1
"""


def _make_temp_dir() -> Path:
    path = TEST_TEMP_ROOT / f"case_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_fix_generator_preserves_structure_and_adds_lock() -> None:
    temp_root = _make_temp_dir()
    try:
        project = temp_root / "project"
        project.mkdir()
        target = project / "counter.py"
        target.write_text(BUGGY_COUNTER, encoding="utf-8")

        state = {
            "run_id": "fix-demo",
            "bug_report": "Race condition in threaded counter update.",
            "project_path": str(project),
            "language": "python",
            "source_extensions": [".py"],
            "test_command": ["python", "-m", "pytest", "-q"],
            "execution_log_path": str(project / "fix_log.jsonl"),
            "classification": {
                "bug_type": "Concurrency Bug",
                "severity": "Medium",
                "summary": "Missing lock around shared-state mutation in counter module.",
                "likely_modules": ["counter"],
            },
            "root_cause": {
                "suspected_file": "counter.py",
                "suspected_function": "increment",
                "evidence": ["counter.py:9 -> current = self.value"],
                "reasoning": "Shared state is updated without synchronization.",
            },
            "status": "analyzed",
        }
        updated = fix_generator_agent(state)
        new_code = Path(updated["patch"]["target_file"]).read_text(encoding="utf-8")
        assert "threading.Lock()" in new_code
        assert "with self._lock:" in new_code
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
