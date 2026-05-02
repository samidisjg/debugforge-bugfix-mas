from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

TEST_SPECS = [
    ("test_tools.py", [
        "test_parse_bug_report_extracts_title_and_keywords",
        "test_code_search_finds_divide_references_with_line_numbers",
        "test_concurrency_scan_finds_thread_risks",
        "test_backup_and_restore_tool_round_trip",
        "test_write_final_report_creates_markdown_file",
        "test_language_detection_and_test_command",
    ]),
    ("test_property_based.py", [
        "test_parse_bug_report_property_constraints",
        "test_backup_restore_round_trip_property",
    ]),
    ("test_state.py", ["test_state_can_hold_advanced_workflow_data"]),
    ("test_sample_project.py", ["test_build_initial_state_resets_demo_project"]),
    ("test_classifier_agent.py", [
        "test_classifier_flags_concurrency_bug",
        "test_classifier_recognizes_validation_bug_context",
        "test_build_initial_state_sets_language_and_command",
    ]),
    ("test_root_cause_agent.py", ["test_root_cause_prefers_source_file_for_concurrency_bug"]),
    ("test_fix_generator_agent.py", ["test_fix_generator_preserves_structure_and_adds_lock"]),
    ("test_tester_agent.py", ["test_tester_writes_final_report"]),
    ("test_rollback_flow.py", ["test_rollback_demo_restores_original_file"]),
    ("test_edge_cases.py", [
        "test_classifier_rejects_low_signal_report_with_low_confidence",
        "test_classifier_respects_fast_mode_for_speed",
        "test_root_cause_handles_empty_search_matches",
        "test_root_cause_prefers_non_test_files",
        "test_fix_generator_rejects_fix_that_deletes_functions",
        "test_fix_generator_low_confidence_when_uncertain",
        "test_classifier_requires_valid_initial_state",
        "test_root_cause_requires_classification",
        "test_fix_generator_requires_root_cause",
        "test_classifier_recognizes_concurrency_keywords",
        "test_root_cause_with_incomplete_classification",
    ]),
    ("test_per_agent_evaluation.py", [
        # Member 1: Classifier & Bug Report Parser
        "TestMember1ClassifierAgent.test_classifier_parses_vague_report_with_low_confidence",
        "TestMember1ClassifierAgent.test_classifier_recognizes_concurrency_bug_keywords",
        "TestMember1ClassifierAgent.test_bug_report_parser_handles_malformed_input",
        # Member 2: Root Cause & Code Search
        "TestMember2RootCauseAgent.test_code_search_prioritizes_non_test_files",
        "TestMember2RootCauseAgent.test_root_cause_with_empty_search_matches_has_low_confidence",
        # Member 3: Fix Generator & Patch Tool
        "TestMember3FixGeneratorAgent.test_patch_tool_creates_backup_and_restores",
        "TestMember3FixGeneratorAgent.test_fix_generator_rejects_uncertain_patches",
        # Member 4: Tester & Test Runner
        "TestMember4TesterAgent.test_test_runner_handles_missing_test_command",
        # State Guards
        "TestStateTransitionGuards.test_guard_before_root_cause_fails_without_classification",
        "TestStateTransitionGuards.test_guard_before_fix_generation_fails_without_root_cause",
        "TestStateTransitionGuards.test_guard_before_validation_fails_without_patch",
        # Hallucination Prevention
        "TestHallucination Prevention.test_classifier_does_not_invent_modules",
        "TestHallucination Prevention.test_root_cause_grounds_evidence_in_actual_files",
    ]),
]


def load_module(module_path: Path):
    spec = spec_from_file_location(module_path.stem, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load test module: {module_path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    """Run the unified evaluation harness without depending on pytest temp fixtures."""
    project_root = Path(__file__).resolve().parents[1]
    evaluations_dir = project_root / "tests" / "evaluations"
    failures: list[str] = []
    total = 0

    for file_name, test_names in TEST_SPECS:
        module = load_module(evaluations_dir / file_name)
        for test_name in test_names:
            total += 1
            try:
                getattr(module, test_name)()
                print(f"PASS {file_name}.{test_name}")
            except Exception as exc:
                failures.append(f"FAIL {file_name}.{test_name}: {exc}")
                print(failures[-1])

    print(f"Executed {total} evaluation checks.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
