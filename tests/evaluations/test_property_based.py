from pathlib import Path
import shutil
from uuid import uuid4

from hypothesis import given, strategies as st

from bug_fixing_mas.classifier_agent.tool_bug_report_parser import parse_bug_report
from bug_fixing_mas.fix_generator_agent.tool_patch_tool import create_backup_file, restore_backup_file


TEST_TEMP_ROOT = Path(__file__).resolve().parents[2] / ".tmp_testdata"
TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)


def _make_temp_dir() -> Path:
    path = TEST_TEMP_ROOT / f"case_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


@given(
    report_text=st.text(min_size=1, max_size=300),
)
def test_parse_bug_report_property_constraints(report_text: str) -> None:
    parsed = parse_bug_report(report_text)
    assert isinstance(parsed.title, str)
    assert parsed.title != ""
    assert isinstance(parsed.body, str)
    assert len(parsed.error_keywords) <= 15
    assert all(keyword == keyword.lower() for keyword in parsed.error_keywords)


@given(
    original=st.text(min_size=1, max_size=200),
    updated=st.text(min_size=1, max_size=200),
)
def test_backup_restore_round_trip_property(original: str, updated: str) -> None:
    temp_root = _make_temp_dir()
    try:
        target = temp_root / "file.py"
        target.write_text(original, encoding="utf-8")
        backup = create_backup_file(str(target))
        target.write_text(updated, encoding="utf-8")
        restore_backup_file(str(target), backup)
        assert target.read_text(encoding="utf-8") == original
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
