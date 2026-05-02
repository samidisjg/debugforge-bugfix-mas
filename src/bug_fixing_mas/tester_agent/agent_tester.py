from __future__ import annotations

from pathlib import Path
from time import perf_counter

from bug_fixing_mas.fix_generator_agent.tool_patch_tool import restore_backup_file
from bug_fixing_mas.tester_agent.tool_final_report import write_final_report, write_final_report_pdf
from bug_fixing_mas.tester_agent.tool_test_runner import compare_bug_behavior, run_project_tests
from bug_fixing_mas.shared.logging_utils import append_jsonl_log
from bug_fixing_mas.shared.prompt_loader import load_prompt
from bug_fixing_mas.shared.state import BugFixState
from bug_fixing_mas.shared.state_validators import ensure_state_is_valid_for_agent


PROMPT_FILE = "tester_prompt.md"


def _build_validator_summary(state: BugFixState, comparison: dict[str, object], restored: bool) -> str:
    test_results = state["test_results"]
    parts = [
        f"Validation command: {test_results['command']}",
        f"Validation passed: {test_results['passed']}",
        f"Rollback performed: {restored}",
        comparison.get("summary", "No before/after comparison available."),
    ]
    if test_results.get("stderr"):
        parts.append("Validation captured stderr output that may indicate remaining issues.")
    if test_results.get("validation_skipped"):
        parts.append("Validation was limited because no explicit test suite was available.")
    return " ".join(parts)


def tester_agent(state: BugFixState) -> BugFixState:
    """Run automated validation after the patch is applied and write final reports."""
    ensure_state_is_valid_for_agent("tester", state)
    started_at = perf_counter()
    prompt_template = load_prompt(PROMPT_FILE)
    result = run_project_tests(state["project_path"], state["language"], state.get("test_command"))
    payload = result.model_dump()
    restored = False
    comparison = compare_bug_behavior(
        state["project_path"],
        state["language"],
        state.get("patch", {}).get("target_file", ""),
        state.get("patch", {}).get("backup_file"),
    )

    if not result.passed and state.get("patch", {}).get("backup_file"):
        restore_backup_file(state["patch"]["target_file"], state["patch"]["backup_file"])
        restored = True

    validation_skipped = result.command == "validation skipped"
    validator_summary = _build_validator_summary({**state, "test_results": {**payload, "restored_original": restored, "validation_skipped": validation_skipped}}, comparison, restored)
    state["test_results"] = {
        **payload,
        "restored_original": restored,
        "validation_skipped": validation_skipped,
        "comparison": comparison,
        "validator_summary": validator_summary,
    }
    state["status"] = "tested" if result.passed else ("rolled_back" if restored else "failed")
    state["final_summary"] = (
        f"Language: {state['language']}. "
        f"Bug type: {state['classification']['bug_type']}. "
        f"Classification confidence: {state['classification'].get('confidence', 0.0)}. "
        f"Root cause file: {state['root_cause']['suspected_file']}. "
        f"Root cause confidence: {state['root_cause'].get('confidence', 0.0)}. "
        f"Patch confidence: {state.get('patch', {}).get('confidence', 0.0)}. "
        f"Tests passed: {result.passed}. "
        f"Validation skipped: {validation_skipped}. "
        f"Rollback performed: {restored}. "
        f"Validator summary: {validator_summary}"
    )

    report_dir = Path(state["execution_log_path"]).resolve().parent
    markdown_path = report_dir / f"final_report_{state['run_id']}.md"
    pdf_path = report_dir / f"final_report_{state['run_id']}.pdf"

    state["final_report_path"] = write_final_report(str(markdown_path), state)
    state["final_report_markdown"] = Path(state["final_report_path"]).read_text(encoding="utf-8")
    state["final_report_pdf_path"] = write_final_report_pdf(str(pdf_path), state["final_report_markdown"])

    append_jsonl_log(
        state["execution_log_path"],
        {
            "run_id": state.get("run_id"),
            "agent": "tester",
            "status": state["status"],
            "duration_ms": round((perf_counter() - started_at) * 1000, 2),
            "input": {
                "project_path": state["project_path"],
                "language": state["language"],
                "test_command": state.get("test_command", []),
                "prompt_contract": prompt_template,
            },
            "tool_calls": [
                {"tool": "load_prompt", "prompt_file": PROMPT_FILE},
                {"tool": "run_project_tests", "command": state["test_results"]["command"]},
                {"tool": "compare_bug_behavior", "comparison": comparison},
                *([
                    {"tool": "restore_backup_file", "target_file": state['patch']['target_file']}
                ] if restored else []),
                {"tool": "write_final_report", "report_path": state["final_report_path"]},
                {"tool": "write_final_report_pdf", "report_path": state["final_report_pdf_path"]},
            ],
            "output": {
                **state["test_results"],
                "final_report_path": state["final_report_path"],
                "final_report_pdf_path": state["final_report_pdf_path"],
            },
        },
    )
    return state
