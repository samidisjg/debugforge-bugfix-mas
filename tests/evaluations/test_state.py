from bug_fixing_mas.shared.state import BugFixState


def test_state_can_hold_advanced_workflow_data() -> None:
    state: BugFixState = {
        "run_id": "demo-run",
        "bug_report": "Example",
        "project_path": "sample_project",
        "language": "python",
        "source_extensions": [".py"],
        "test_command": ["python", "-m", "pytest", "-q"],
        "execution_log_path": "logs/agent_runs.jsonl",
        "search_matches": [],
        "status": "received",
    }
    assert state["run_id"] == "demo-run"
    assert state["language"] == "python"
    assert state["status"] == "received"
