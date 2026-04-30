from pathlib import Path
import shutil
from uuid import uuid4

from bug_fixing_mas.classifier_agent.tool_bug_report_parser import parse_bug_report
from bug_fixing_mas.root_cause_agent.tool_code_search import scan_concurrency_risks, search_source_files
from bug_fixing_mas.fix_generator_agent.tool_patch_tool import create_backup_file, restore_backup_file
from bug_fixing_mas.tester_agent.tool_final_report import write_final_report
from bug_fixing_mas.service import _augment_bug_report_with_discovery, _normalize_language
from bug_fixing_mas.shared.language_config import detect_project_language, determine_test_command


TEST_TEMP_ROOT = Path(__file__).resolve().parents[2] / ".tmp_testdata"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


def _make_temp_dir() -> Path:
    path = TEST_TEMP_ROOT / f"case_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_parse_bug_report_extracts_title_and_keywords() -> None:
    parsed = parse_bug_report("Division bug\nZero division should raise an error.")
    assert parsed.title == "Division bug"
    assert "division" in parsed.error_keywords


def test_code_search_finds_divide_references_with_line_numbers() -> None:
    matches = search_source_files("sample_project", ["divide"], [".py"])
    assert matches
    assert any("calculator.py" in str(match["file"]) for match in matches)
    assert all("line_number" in match for match in matches)


def test_concurrency_scan_finds_thread_risks() -> None:
    findings = scan_concurrency_risks("sample_projects/python_concurrency", [".py"])
    assert findings
    assert any("thread" in str(item["snippet"]).lower() or "sleep" in str(item["snippet"]).lower() for item in findings)


def test_backup_and_restore_tool_round_trip() -> None:
    temp_root = _make_temp_dir()
    try:
        target = temp_root / "demo.py"
        target.write_text("print('old')\n", encoding="utf-8")
        backup = create_backup_file(str(target))
        target.write_text("print('new')\n", encoding="utf-8")
        restore_backup_file(str(target), backup)
        assert target.read_text(encoding="utf-8") == "print('old')\n"
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_write_final_report_creates_markdown_file() -> None:
    temp_root = _make_temp_dir()
    try:
        report_path = temp_root / "report.md"
        state = {
            "run_id": "demo-run",
            "language": "python",
            "project_path": "sample_project",
            "status": "tested",
            "bug_report": "example bug",
            "classification": {"bug_type": "Logic Bug", "severity": "High", "summary": "bad output", "likely_modules": ["calculator"]},
            "root_cause": {"suspected_file": "calculator.py", "suspected_function": "divide", "reasoning": "bad branch", "evidence": ["calculator.py:5 -> return 0"]},
            "patch": {"target_file": "calculator.py", "backup_file": "calculator.py.bak", "change_summary": "fixed branch"},
            "test_results": {"command": "python -m pytest -q", "passed": True, "restored_original": False, "summary": "Tests passed."},
            "final_summary": "Tests passed.",
        }
        output = write_final_report(str(report_path), state)
        assert Path(output).exists()
        assert "# Bug Fixing MAS Report" in report_path.read_text(encoding="utf-8")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_language_detection_and_test_command() -> None:
    assert detect_project_language("sample_project") == "python"
    assert detect_project_language("sample_projects/python_concurrency") == "python"
    assert detect_project_language("sample_projects/javascript") == "javascript"
    assert detect_project_language("sample_projects/java") == "java"
    assert detect_project_language("sample_projects/go") == "go"
    assert determine_test_command("sample_projects/go", "go") == ["go", "test", "./..."]


def test_custom_upload_language_beats_dropdown_default() -> None:
    custom_files = [{"filename": "LibraryClientService.java", "content": "public class LibraryClientService {}\n"}]
    assert _normalize_language("python", None, custom_files) == "java"


def test_low_signal_report_is_augmented_with_discovery_hints() -> None:
    temp_root = _make_temp_dir()
    try:
        java_file = temp_root / "LibraryClientService.java"
        java_file.write_text(
            """
public class LibraryClientService {
    void call() {
        client.retrieve().onStatus(HttpStatusCode::isError,
            response -> response.bodyToMono(String.class)
                .map(body -> new LibraryServiceException(body)));
    }
}
""".strip()
            + "\n",
            encoding="utf-8",
        )
        augmented = _augment_bug_report_with_discovery("fix bug", temp_root, "java")
        assert "Auto-discovery hints from static scan" in augmented
        assert "reactive onStatus with map(Exception)" in augmented
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
