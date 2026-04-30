"""Edge case and negative tests for agent reliability and hallucination detection."""

from pathlib import Path
import shutil
from uuid import uuid4

from bug_fixing_mas.classifier_agent.agent_classifier import classifier_agent
from bug_fixing_mas.root_cause_agent.agent_root_cause import root_cause_agent
from bug_fixing_mas.fix_generator_agent.agent_fix_generator import fix_generator_agent
from bug_fixing_mas.shared.state_validators import StateValidationError, ensure_state_is_valid_for_agent


TEST_TEMP_ROOT = Path(__file__).resolve().parents[2] / ".tmp_testdata"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


def _make_temp_dir() -> Path:
    path = TEST_TEMP_ROOT / f"edge_case_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


# ============ CLASSIFIER EDGE CASES ============

def test_classifier_rejects_low_signal_report_with_low_confidence() -> None:
    """Classifier should assign low confidence to vague or empty bug reports."""
    state = {
        "run_id": "edge-case-1",
        "bug_report": "bug",  # Extremely vague
        "project_path": "sample_project",
        "language": "python",
        "source_extensions": [".py"],
        "test_command": ["python", "-m", "pytest", "-q"],
        "execution_log_path": "logs/test_classifier_edge.jsonl",
        "status": "received",
    }
    updated = classifier_agent(state)
    assert updated["classification"]["confidence"] < 0.6, "Classifier should mark vague reports as low-confidence"


def test_classifier_respects_fast_mode_for_speed() -> None:
    """Classifier should use fast heuristic path when fast_mode is True."""
    state = {
        "run_id": "edge-case-2",
        "bug_report": "divide by zero returns 0",
        "project_path": "sample_project",
        "language": "python",
        "source_extensions": [".py"],
        "test_command": ["python", "-m", "pytest", "-q"],
        "execution_log_path": "logs/test_classifier_fast.jsonl",
        "fast_mode": True,
        "status": "received",
    }
    updated = classifier_agent(state)
    # Should complete quickly and classify without LLM call
    assert updated["classification"]["bug_type"] in ["ArithmeticError", "Behavioral Bug"]


# ============ ROOT CAUSE EDGE CASES ============

def test_root_cause_handles_empty_search_matches() -> None:
    """Root cause should not crash or hallucinate when search matches are empty."""
    state = {
        "run_id": "edge-case-3",
        "bug_report": "some bug in nonexistent code",
        "project_path": "sample_project",
        "language": "python",
        "source_extensions": [".py"],
        "test_command": ["python", "-m", "pytest", "-q"],
        "execution_log_path": "logs/test_root_cause_empty.jsonl",
        "classification": {
            "bug_type": "Unknown",
            "severity": "Low",
            "summary": "Unclassifiable bug",
            "likely_modules": [],
            "confidence": 0.3,
        },
        "status": "classified",
        "search_matches": [],  # Empty evidence
        "static_signals": [],
    }
    # Should still produce output but with low confidence
    updated = root_cause_agent(state)
    assert "root_cause" in updated
    assert updated["root_cause"]["confidence"] < 0.5, "Should assign low confidence when no evidence found"


def test_root_cause_prefers_non_test_files() -> None:
    """Root cause should prefer implementation files over test files when both match."""
    state = {
        "run_id": "edge-case-4",
        "bug_report": "Race condition in counter update.",
        "project_path": "sample_projects/python_concurrency",
        "language": "python",
        "source_extensions": [".py"],
        "test_command": ["python", "-m", "pytest", "-q"],
        "execution_log_path": "logs/test_root_cause_nontest.jsonl",
        "classification": {
            "bug_type": "Concurrency Bug",
            "severity": "High",
            "summary": "Missing lock around shared-state mutation.",
            "likely_modules": ["counter"],
            "confidence": 0.85,
        },
        "status": "classified",
    }
    updated = root_cause_agent(state)
    # Should identify counter.py, not test files
    assert updated["root_cause"]["suspected_file"] != "test_counter.py"


# ============ FIX GENERATOR EDGE CASES ============

def test_fix_generator_rejects_fix_that_deletes_functions() -> None:
    """Fix generator should detect and penalize patches that delete functions."""
    temp_root = _make_temp_dir()
    try:
        project = temp_root / "project"
        project.mkdir()
        original_code = (
            "def add(a: float, b: float) -> float:\n"
            "    return a + b\n\n"
            "def divide(a: float, b: float) -> float:\n"
            "    if b == 0:\n"
            "        return 0\n"
            "    return a / b\n"
        )
        (project / "calculator.py").write_text(original_code, encoding="utf-8")

        state = {
            "run_id": "edge-case-5",
            "bug_report": "Fix divide by zero",
            "project_path": str(project),
            "language": "python",
            "source_extensions": [".py"],
            "test_command": ["python", "-m", "pytest", "-q"],
            "execution_log_path": str(temp_root / "logs" / "edge_case.jsonl"),
            "classification": {
                "bug_type": "ArithmeticError",
                "severity": "Medium",
                "summary": "Divide returns 0 instead of raising.",
                "likely_modules": ["calculator"],
                "confidence": 0.9,
            },
            "root_cause": {
                "suspected_file": "calculator.py",
                "suspected_function": "divide",
                "evidence": ["calculator.py:5 -> return 0"],
                "reasoning": "Divide returns 0 instead of raising.",
                "confidence": 0.9,
            },
            "status": "analyzed",
            "llm_context": {},
        }
        updated = fix_generator_agent(state)
        # The agent should preserve the add function
        assert "def add(" in updated["patch"]["new_code"], "Patch should preserve unrelated functions"
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_fix_generator_low_confidence_when_uncertain() -> None:
    """Fix generator should assign low confidence when the fix is uncertain."""
    temp_root = _make_temp_dir()
    try:
        project = temp_root / "project"
        project.mkdir()
        (project / "mystery.py").write_text("# unclear code\n", encoding="utf-8")

        state = {
            "run_id": "edge-case-6",
            "bug_report": "Something is wrong somewhere",
            "project_path": str(project),
            "language": "python",
            "source_extensions": [".py"],
            "test_command": ["python", "-m", "pytest", "-q"],
            "execution_log_path": str(temp_root / "logs" / "edge_case.jsonl"),
            "classification": {
                "bug_type": "Unknown",
                "severity": "Low",
                "summary": "Very unclear",
                "likely_modules": [],
                "confidence": 0.2,
            },
            "root_cause": {
                "suspected_file": "mystery.py",
                "suspected_function": "unknown",
                "evidence": [],
                "reasoning": "No clear evidence",
                "confidence": 0.25,
            },
            "status": "analyzed",
            "llm_context": {},
        }
        updated = fix_generator_agent(state)
        assert updated["patch"]["confidence"] < 0.5, "Patch should have low confidence when root cause is uncertain"
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


# ============ STATE VALIDATION EDGE CASES ============

def test_classifier_requires_valid_initial_state() -> None:
    """Classifier should reject incomplete initial state."""
    incomplete_state = {
        "run_id": "edge-case-7",
        # Missing bug_report, project_path, etc.
        "language": "python",
    }
    try:
        ensure_state_is_valid_for_agent("classifier", incomplete_state)
        assert False, "Should have raised StateValidationError"
    except StateValidationError as exc:
        assert "missing required fields" in str(exc).lower()


def test_root_cause_requires_classification() -> None:
    """Root cause should reject state without classification."""
    incomplete_state = {
        "run_id": "edge-case-8",
        "bug_report": "some bug",
        "project_path": "sample_project",
        "language": "python",
        # Missing classification
    }
    try:
        ensure_state_is_valid_for_agent("root_cause", incomplete_state)
        assert False, "Should have raised StateValidationError"
    except StateValidationError as exc:
        assert "classification" in str(exc).lower()


def test_fix_generator_requires_root_cause() -> None:
    """Fix generator should reject state without root cause."""
    incomplete_state = {
        "run_id": "edge-case-9",
        "bug_report": "some bug",
        "classification": {"bug_type": "Logic Bug"},
        # Missing root_cause
    }
    try:
        ensure_state_is_valid_for_agent("fix_generator", incomplete_state)
        assert False, "Should have raised StateValidationError"
    except StateValidationError as exc:
        assert "root cause" in str(exc).lower()


# ============ CONCURRENCY BUG SPECIFIC TESTS ============

def test_classifier_recognizes_concurrency_keywords() -> None:
    """Classifier should detect concurrency bug from explicit keywords."""
    state = {
        "run_id": "edge-case-10",
        "bug_report": "Race condition with threading and shared mutable state causing deadlock.",
        "project_path": "sample_projects/python_concurrency",
        "language": "python",
        "source_extensions": [".py"],
        "test_command": ["python", "-m", "pytest", "-q"],
        "execution_log_path": "logs/test_classifier_concurrency.jsonl",
        "status": "received",
    }
    updated = classifier_agent(state)
    assert updated["classification"]["bug_type"] == "Concurrency Bug", "Should classify explicit concurrency keywords"


# ============ VALIDATION ERROR HANDLING ============

def test_root_cause_with_incomplete_classification() -> None:
    """Root cause should handle classification with missing optional fields gracefully."""
    state = {
        "run_id": "edge-case-11",
        "bug_report": "divide by zero",
        "project_path": "sample_project",
        "language": "python",
        "source_extensions": [".py"],
        "test_command": ["python", "-m", "pytest", "-q"],
        "execution_log_path": "logs/test_root_cause_incomplete.jsonl",
        "classification": {
            "bug_type": "ArithmeticError",
            "severity": "Medium",
            # Only required fields, missing optional ones
            "summary": "divide by zero",
        },
        "status": "classified",
    }
    # Should not crash; should fill in missing optional fields
    updated = root_cause_agent(state)
    assert "root_cause" in updated
    assert updated["root_cause"]["confidence"] >= 0.0
