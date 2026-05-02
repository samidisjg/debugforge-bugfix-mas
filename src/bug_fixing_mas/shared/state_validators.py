from __future__ import annotations

from typing import Any

from bug_fixing_mas.shared.state import BugFixState


class StateValidationError(Exception):
    """Raised when a state transition requirement is not met."""
    pass


def validate_initial_state(state: BugFixState) -> None:
    """Validate that the initial state has all required fields before classification."""
    required = ["run_id", "bug_report", "project_path", "language", "execution_log_path"]
    missing = [key for key in required if not state.get(key)]
    if missing:
        raise StateValidationError(f"Initial state missing required fields: {missing}")


def validate_before_root_cause(state: BugFixState) -> None:
    """Validate that classification exists and has minimum required fields."""
    if "classification" not in state:
        raise StateValidationError("Classification not found in state; root cause analysis cannot proceed.")
    
    classification = state.get("classification", {})
    required_fields = ["bug_type", "severity", "summary"]
    missing = [key for key in required_fields if key not in classification]
    if missing:
        raise StateValidationError(f"Classification incomplete; missing fields: {missing}")


def validate_before_fix_generator(state: BugFixState) -> None:
    """Validate that root cause analysis is complete and has minimum required fields."""
    if "root_cause" not in state:
        raise StateValidationError("Root cause not found in state; fix generation cannot proceed.")
    
    root_cause = state.get("root_cause", {})
    required_fields = ["suspected_file", "suspected_function", "reasoning"]
    missing = [key for key in required_fields if key not in root_cause]
    if missing:
        raise StateValidationError(f"Root cause incomplete; missing fields: {missing}")


def validate_before_tester(state: BugFixState) -> None:
    """Validate that patch has been generated and state is ready for testing."""
    if "patch" not in state:
        raise StateValidationError("Patch not found in state; testing cannot proceed.")
    
    patch = state.get("patch", {})
    required_fields = ["target_file", "new_code", "change_summary"]
    missing = [key for key in required_fields if key not in patch]
    if missing:
        raise StateValidationError(f"Patch incomplete; missing fields: {missing}")


def validate_final_state(state: BugFixState) -> None:
    """Validate that the final state has all required artifacts for reporting."""
    required = ["run_id", "status", "test_results", "final_summary"]
    missing = [key for key in required if not state.get(key)]
    if missing:
        raise StateValidationError(f"Final state missing required fields: {missing}")


def ensure_state_is_valid_for_agent(agent_name: str, state: BugFixState) -> None:
    """
    Route-based state validation: ensure state is valid before an agent runs.
    
    This prevents agents from executing with incomplete context and provides
    clear error messages when state transitions fail.
    """
    if agent_name == "classifier":
        validate_initial_state(state)
    elif agent_name == "root_cause":
        validate_before_root_cause(state)
    elif agent_name == "fix_generator":
        validate_before_fix_generator(state)
    elif agent_name == "tester":
        validate_before_tester(state)
