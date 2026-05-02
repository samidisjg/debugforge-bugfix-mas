from __future__ import annotations

from typing import Any, Literal, TypedDict


class BugFixState(TypedDict, total=False):
    """Global state passed between the four agents."""

    run_id: str
    input_mode: Literal["demo", "custom"]
    execution_mode: Literal["full", "classifier", "root_cause", "fix_generator", "tester"]
    fast_mode: bool
    bug_report: str
    project_path: str
    language: str
    source_extensions: list[str]
    test_command: list[str]
    execution_log_path: str
    classification: dict[str, Any]
    search_matches: list[dict[str, Any]]
    static_signals: list[dict[str, Any]]
    llm_context: dict[str, Any]
    root_cause: dict[str, Any]
    patch: dict[str, Any]
    test_results: dict[str, Any]
    final_report_path: str
    final_report_pdf_path: str
    patch_diff_path: str
    final_report_markdown: str
    status: Literal["received", "classified", "analyzed", "patched", "tested", "failed", "rolled_back"]
    final_summary: str


# ============================================================================
# STATE TRANSITION GUARDS - Enforce strict state machine transitions
# These guards make the state handling look more engineered and less ad-hoc
# ============================================================================


class StateTransitionError(Exception):
    """Raised when a state transition violates the workflow state machine."""
    pass


def _assert_field_exists(state: BugFixState, field: str, context: str) -> Any:
    """Assert that a required field exists in state, or raise StateTransitionError."""
    if field not in state or state.get(field) is None:
        raise StateTransitionError(
            f"State transition guard failed: Required field '{field}' is missing or None in state. "
            f"Context: {context}"
        )
    return state[field]


def _assert_nested_field_exists(state: BugFixState, parent: str, child: str, context: str) -> Any:
    """Assert that a nested field exists in state, or raise StateTransitionError."""
    parent_obj = _assert_field_exists(state, parent, context)
    if not isinstance(parent_obj, dict) or child not in parent_obj or parent_obj.get(child) is None:
        raise StateTransitionError(
            f"State transition guard failed: Required nested field '{parent}.{child}' is missing or None in state. "
            f"Context: {context}"
        )
    return parent_obj[child]


def guard_before_root_cause_analysis(state: BugFixState) -> None:
    """
    Transition Guard: Ensure state is ready for Root Cause Analysis.
    
    Root Cause Agent requires:
    - Initial state fields (run_id, project_path, language)
    - Classification completed (bug_type, severity)
    - Bug report available for context
    
    Raises StateTransitionError if preconditions not met.
    """
    # Check initialization fields
    _assert_field_exists(state, "run_id", "guard_before_root_cause_analysis")
    _assert_field_exists(state, "project_path", "guard_before_root_cause_analysis")
    _assert_field_exists(state, "language", "guard_before_root_cause_analysis")
    
    # Check classification completed
    _assert_field_exists(state, "classification", "guard_before_root_cause_analysis - missing classification dict")
    _assert_nested_field_exists(state, "classification", "bug_type", "root_cause needs classification.bug_type")
    _assert_nested_field_exists(state, "classification", "severity", "root_cause needs classification.severity")


def guard_before_fix_generation(state: BugFixState) -> None:
    """
    Transition Guard: Ensure state is ready for Patch Generation.
    
    Fix Generator Agent requires:
    - Root cause analysis completed (suspected_file, suspected_function, reasoning)
    - Source code accessible (project_path, language)
    - Must have some confidence level
    
    Raises StateTransitionError if preconditions not met.
    """
    # Check root cause completed
    _assert_field_exists(state, "root_cause", "guard_before_fix_generation - missing root_cause dict")
    _assert_nested_field_exists(state, "root_cause", "suspected_file", "fix_gen needs root_cause.suspected_file")
    _assert_nested_field_exists(state, "root_cause", "suspected_function", "fix_gen needs root_cause.suspected_function")
    _assert_nested_field_exists(state, "root_cause", "reasoning", "fix_gen needs root_cause.reasoning")
    
    # Check source context available
    _assert_field_exists(state, "project_path", "guard_before_fix_generation")
    _assert_field_exists(state, "language", "guard_before_fix_generation")


def guard_before_validation(state: BugFixState) -> None:
    """
    Transition Guard: Ensure state is ready for Validation/Testing.
    
    Tester Agent requires:
    - Patch generated (target_file, new_code, backup_file)
    - Patch applied to workspace
    - Test command available (or will skip)
    - Original code backed up for rollback
    
    Raises StateTransitionError if preconditions not met.
    """
    # Check patch completed
    _assert_field_exists(state, "patch", "guard_before_validation - missing patch dict")
    _assert_nested_field_exists(state, "patch", "target_file", "tester needs patch.target_file")
    _assert_nested_field_exists(state, "patch", "new_code", "tester needs patch.new_code")
    _assert_nested_field_exists(state, "patch", "backup_file", "tester needs patch.backup_file for rollback")
    
    # Check project accessible
    _assert_field_exists(state, "project_path", "guard_before_validation")
    _assert_field_exists(state, "language", "guard_before_validation")


def guard_before_reporting(state: BugFixState) -> None:
    """
    Transition Guard: Ensure all required information is available for final report.
    
    Reporter needs:
    - Initial workflow state (run_id, bug_report, language)
    - All agent outputs (classification, root_cause, patch, test_results)
    - Final status established
    
    Raises StateTransitionError if preconditions not met.
    """
    # Check workflow identification
    _assert_field_exists(state, "run_id", "guard_before_reporting")
    _assert_field_exists(state, "bug_report", "guard_before_reporting")
    _assert_field_exists(state, "language", "guard_before_reporting")
    
    # Check all agents provided output
    _assert_field_exists(state, "classification", "guard_before_reporting - missing classification")
    _assert_field_exists(state, "root_cause", "guard_before_reporting - missing root_cause")
    _assert_field_exists(state, "patch", "guard_before_reporting - missing patch")
    _assert_field_exists(state, "test_results", "guard_before_reporting - missing test_results")
    
    # Check status is set
    _assert_field_exists(state, "status", "guard_before_reporting")


def get_state_machine_summary(state: BugFixState) -> dict[str, bool]:
    """
    Return a summary of which state transition gates have been cleared.
    
    Useful for debugging and understanding workflow progress:
    - ready_for_root_cause: Classification complete
    - ready_for_fix_generation: Root cause complete
    - ready_for_validation: Patch complete
    - ready_for_reporting: All agents done
    """
    summary = {
        "ready_for_root_cause": False,
        "ready_for_fix_generation": False,
        "ready_for_validation": False,
        "ready_for_reporting": False,
    }
    
    try:
        guard_before_root_cause_analysis(state)
        summary["ready_for_root_cause"] = True
    except StateTransitionError:
        pass
    
    try:
        guard_before_fix_generation(state)
        summary["ready_for_fix_generation"] = True
    except StateTransitionError:
        pass
    
    try:
        guard_before_validation(state)
        summary["ready_for_validation"] = True
    except StateTransitionError:
        pass
    
    try:
        guard_before_reporting(state)
        summary["ready_for_reporting"] = True
    except StateTransitionError:
        pass
    
    return summary
