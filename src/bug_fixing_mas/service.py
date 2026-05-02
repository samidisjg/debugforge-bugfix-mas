from __future__ import annotations

from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

from bug_fixing_mas.graph import build_graph
from bug_fixing_mas.classifier_agent.agent_classifier import classifier_agent
from bug_fixing_mas.root_cause_agent.agent_root_cause import root_cause_agent
from bug_fixing_mas.fix_generator_agent.agent_fix_generator import fix_generator_agent
from bug_fixing_mas.tester_agent.agent_tester import tester_agent
from bug_fixing_mas.shared.language_config import (
    detect_project_language,
    determine_test_command,
    get_language_config,
)
from bug_fixing_mas.shared.state import (
    guard_before_fix_generation,
    guard_before_reporting,
    guard_before_root_cause_analysis,
    guard_before_validation,
)


DEFAULT_BUG_REPORT = (
    "Division by zero is returning 0 instead of raising an error.\n"
    "Users expect ZeroDivisionError for divide(5, 0).\n"
    "The failing behavior is in the calculator utility."
)

DEFAULT_BUGGY_CALCULATOR = """def add(a: float, b: float) -> float:
    return a + b


def divide(a: float, b: float) -> float:
    if b == 0:
        return 0
    return a / b
"""

DEFAULT_CONCURRENCY_BUG = """import threading
import time


class Counter:
    def __init__(self) -> None:
        self.value = 0

    def increment(self) -> None:
        current = self.value
        time.sleep(0.0001)
        self.value = current + 1


def worker(counter: Counter, iterations: int) -> None:
    for _ in range(iterations):
        counter.increment()


def run_workers(num_threads: int = 20, iterations: int = 100) -> int:
    counter = Counter()
    threads = [threading.Thread(target=worker, args=(counter, iterations)) for _ in range(num_threads)]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    return counter.value
"""

DEFAULT_VALIDATION_BUG = """def normalize_age(age: int) -> int:
    if age < 0:
        return age
    return age
"""

DEFAULT_WRONG_RETURN_BUG = """def is_even(value: int) -> bool:
    return True
"""

DEFAULT_FILENAMES = {
    "python": "main.py",
    "javascript": "main.js",
    "java": "Main.java",
    "go": "main.go",
}

DEFAULT_TEST_FILENAMES = {
    "python": "test_main.py",
    "javascript": "main.test.js",
    "java": "MainTest.java",
    "go": "main_test.go",
}

RUNTIME_WORKSPACE_ROOT = Path(gettempdir()) / "bug_fixing_mas_runtime_workspaces"


LOW_SIGNAL_BUG_REPORT_PHRASES = {
    "fix bug",
    "find bug",
    "identify bug",
    "bug in code",
    "code not working",
    "something is wrong",
    "check code",
}


EXECUTION_MODE_SEQUENCE = [
    ("classifier", classifier_agent),
    ("root_cause", root_cause_agent),
    ("fix_generator", fix_generator_agent),
    ("tester", tester_agent),
]


def _validate_execution_mode(execution_mode: str) -> str:
    allowed = {"full", "classifier", "root_cause", "fix_generator", "tester"}
    normalized = execution_mode.strip().lower()
    if normalized not in allowed:
        raise ValueError(f"Unsupported execution mode: {execution_mode}")
    return normalized


def _run_selected_execution_mode(initial_state: dict[str, object], execution_mode: str) -> dict[str, object]:
    normalized_mode = _validate_execution_mode(execution_mode)
    initial_state["execution_mode"] = normalized_mode

    if normalized_mode == "full":
        app = build_graph()
        return app.invoke(initial_state)

    state = initial_state
    for agent_name, agent_fn in EXECUTION_MODE_SEQUENCE:
        if agent_name == "root_cause":
            guard_before_root_cause_analysis(state)
        elif agent_name == "fix_generator":
            guard_before_fix_generation(state)
        elif agent_name == "tester":
            guard_before_validation(state)

        state = agent_fn(state)
        if agent_name == normalized_mode:
            break

    if normalized_mode == "tester":
        guard_before_reporting(state)

    return state


def _infer_language_from_candidate(candidate: str) -> str | None:
    suffix = Path(candidate).suffix.lower()
    if suffix == ".py":
        return "python"
    if suffix in {".js", ".mjs", ".cjs"}:
        return "javascript"
    if suffix == ".java":
        return "java"
    if suffix == ".go":
        return "go"
    return None


def _is_low_signal_bug_report(report_text: str) -> bool:
    normalized = " ".join(report_text.strip().lower().split())
    if not normalized:
        return True
    if normalized in LOW_SIGNAL_BUG_REPORT_PHRASES:
        return True
    if len(normalized.split()) <= 5:
        return True
    return False


def _discover_bug_hints(project_path: Path, language: str) -> list[str]:
    hints: list[str] = []
    language_config = get_language_config(language)
    files = sorted(project_path.rglob("*"))
    source_files = [path for path in files if path.is_file() and path.suffix in language_config.source_extensions][:25]

    for file_path in source_files:
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        file_name = file_path.name
        lowered = content.lower()

        if "todo" in lowered or "fixme" in lowered:
            hints.append(f"{file_name}: contains TODO/FIXME markers that may indicate incomplete logic.")

        if language == "java":
            if ".onstatus(" in lowered and ".map(" in lowered and "exception" in lowered:
                hints.append(f"{file_name}: reactive onStatus with map(Exception) may not propagate errors correctly.")
            if "catch (exception" in lowered and "throw" not in lowered:
                hints.append(f"{file_name}: catch(Exception) block without rethrow can mask failures.")

        if language == "python" and "if b == 0" in lowered and "return 0" in lowered:
            hints.append(f"{file_name}: divide-by-zero branch returns 0 instead of raising an error.")

        if language == "python" and "[0]" in lowered and "if not" not in lowered:
            hints.append(f"{file_name}: first-element access may raise IndexError when the collection is empty.")

        if language == "java" and "if (b == 0)" in lowered and "return 0;" in lowered:
            hints.append(f"{file_name}: divide-by-zero branch returns 0 instead of throwing an exception.")

        if language == "javascript" and "if (b === 0)" in lowered and "return 0" in lowered:
            hints.append(f"{file_name}: divide-by-zero branch returns 0, which may hide invalid input.")

        if language == "go" and "if b == 0" in lowered and "return 0" in lowered:
            hints.append(f"{file_name}: divide-by-zero branch returns 0, potentially masking runtime faults.")

        if len(hints) >= 3:
            break

    deduped: list[str] = []
    seen: set[str] = set()
    for hint in hints:
        if hint not in seen:
            seen.add(hint)
            deduped.append(hint)
    return deduped[:3]


def _augment_bug_report_with_discovery(report_text: str, project_path: Path, language: str) -> str:
    if not _is_low_signal_bug_report(report_text):
        return report_text.strip()
    hints = _discover_bug_hints(project_path, language)
    if not hints:
        return report_text.strip()
    bullets = "\n".join(f"- {hint}" for hint in hints)
    return (
        f"{report_text.strip()}\n\n"
        f"Auto-discovery hints from static scan:\n"
        f"{bullets}\n"
    )


def reset_demo_project(project_root: Path, project_path: Path, language: str) -> None:
    """Reset known demo projects to buggy baselines for repeatable demos."""
    if language != "python":
        return

    sample_project = (project_root / "sample_project").resolve()
    concurrency_project = (project_root / "sample_projects" / "python_concurrency").resolve()
    rollback_project = (project_root / "sample_projects" / "python_rollback_demo").resolve()
    validation_project = (project_root / "sample_projects" / "python_validation").resolve()
    wrong_return_project = (project_root / "sample_projects" / "python_wrong_return").resolve()
    resolved_project = project_path.resolve()

    if resolved_project == sample_project or resolved_project == rollback_project:
        (project_path / "calculator.py").write_text(DEFAULT_BUGGY_CALCULATOR, encoding="utf-8")
        return

    if resolved_project == concurrency_project:
        (project_path / "counter.py").write_text(DEFAULT_CONCURRENCY_BUG, encoding="utf-8")
        return

    if resolved_project == validation_project:
        (project_path / "validator.py").write_text(DEFAULT_VALIDATION_BUG, encoding="utf-8")
        return

    if resolved_project == wrong_return_project:
        (project_path / "parity.py").write_text(DEFAULT_WRONG_RETURN_BUG, encoding="utf-8")


def _normalize_language(language: str | None, source_filename: str | None, custom_files: list[dict[str, str]] | None = None) -> str:
    candidates: list[str] = []
    if custom_files:
        candidates.extend(file_info.get("filename", "") for file_info in custom_files)
    if source_filename:
        candidates.append(source_filename)
    for candidate in candidates:
        inferred_language = _infer_language_from_candidate(candidate)
        if inferred_language:
            return inferred_language
    if language:
        return language.lower()
    return "python"


def _default_filename_for_language(language: str) -> str:
    return DEFAULT_FILENAMES.get(language, DEFAULT_FILENAMES["python"])


def _default_test_filename_for_language(language: str) -> str:
    return DEFAULT_TEST_FILENAMES.get(language, DEFAULT_TEST_FILENAMES["python"])


def _is_test_file(filename: str) -> bool:
    name = Path(filename).name.lower()
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith(".test.js")
        or name.endswith(".spec.js")
        or name.endswith("test.java")
        or name.endswith("_test.go")
    )


def _custom_test_command(language: str, workspace_path: Path, has_test_file: bool) -> list[str]:
    if not has_test_file:
        return []
    if language == "python":
        return ["python", "-m", "pytest", "-q"]
    if language == "go":
        return ["go", "test", "./..."]
    if language == "javascript" and (workspace_path / "package.json").exists():
        return determine_test_command(str(workspace_path), language)
    if language == "java" and ((workspace_path / "pom.xml").exists() or (workspace_path / "build.gradle").exists()):
        return determine_test_command(str(workspace_path), language)
    return []


def _normalize_custom_files(
    *,
    language: str,
    source_code: str | None,
    source_filename: str | None,
    test_code: str | None,
    test_filename: str | None,
    custom_files: list[dict[str, str]] | None,
) -> list[dict[str, str]]:
    files: list[dict[str, str]] = []

    for file_info in custom_files or []:
        filename = (file_info.get("filename") or "").strip()
        content = file_info.get("content") or ""
        if filename and content.strip():
            files.append({"filename": filename, "content": content.rstrip() + "\n"})

    if source_code and source_code.strip():
        files.append(
            {
                "filename": (source_filename or _default_filename_for_language(language)).strip(),
                "content": source_code.strip() + "\n",
            }
        )

    if test_code and test_code.strip():
        files.append(
            {
                "filename": (test_filename or _default_test_filename_for_language(language)).strip(),
                "content": test_code.strip() + "\n",
            }
        )

    deduped: dict[str, str] = {}
    for file_info in files:
        deduped[file_info["filename"]] = file_info["content"]
    return [{"filename": filename, "content": content} for filename, content in deduped.items()]


def create_custom_workspace(
    *,
    project_root: Path,
    run_id: str,
    language: str,
    files: list[dict[str, str]],
) -> tuple[Path, list[str]]:
    """Create a temporary local project from pasted or uploaded files."""
    workspace_path = RUNTIME_WORKSPACE_ROOT / run_id
    workspace_path.mkdir(parents=True, exist_ok=True)

    for file_info in files:
        relative_path = Path(file_info["filename"])
        target_path = workspace_path / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(file_info["content"], encoding="utf-8")

    has_test_file = any(_is_test_file(file_info["filename"]) for file_info in files)

    if language == "python" and has_test_file:
        (workspace_path / "pyproject.toml").write_text(
            "[tool.pytest.ini_options]\npythonpath = [\".\"]\n",
            encoding="utf-8",
        )

    test_command = _custom_test_command(language, workspace_path, has_test_file)
    return workspace_path, test_command


def build_initial_state(
    project_root: Path,
    bug_report: str,
    project_path: str | None,
    log_path: str | None,
    language: str | None,
    *,
    run_id: str | None = None,
    test_command_override: list[str] | None = None,
    fast_mode: bool = False,
    execution_mode: str = "full",
) -> dict[str, object]:
    """Build the initial shared state for a run."""
    resolved_project_path = Path(project_path) if project_path else project_root / "sample_project"
    resolved_language = language or detect_project_language(str(resolved_project_path))
    language_config = get_language_config(resolved_language)
    resolved_log_path = Path(log_path) if log_path else project_root / "logs" / "agent_runs.jsonl"
    reset_demo_project(project_root, resolved_project_path, resolved_language)
    return {
        "run_id": run_id or str(uuid4()),
        "bug_report": bug_report,
        "project_path": str(resolved_project_path),
        "language": resolved_language,
        "source_extensions": list(language_config.source_extensions),
        "test_command": test_command_override if test_command_override is not None else determine_test_command(str(resolved_project_path), resolved_language),
        "execution_log_path": str(resolved_log_path),
        "fast_mode": fast_mode,
        "execution_mode": execution_mode,
        "status": "received",
    }


def run_bug_fixing_workflow(
    *,
    project_root: Path,
    bug_report: str,
    project_path: str | None = None,
    log_path: str | None = None,
    language: str | None = None,
    custom_source_code: str | None = None,
    custom_source_filename: str | None = None,
    custom_test_code: str | None = None,
    custom_test_filename: str | None = None,
    custom_files: list[dict[str, str]] | None = None,
    fast_mode: bool = False,
    execution_mode: str = "full",
) -> dict[str, object]:
    """Run the end-to-end graph and return the final state."""
    run_id = str(uuid4())

    normalized_language = _normalize_language(language, custom_source_filename, custom_files)
    normalized_files = _normalize_custom_files(
        language=normalized_language,
        source_code=custom_source_code,
        source_filename=custom_source_filename,
        test_code=custom_test_code,
        test_filename=custom_test_filename,
        custom_files=custom_files,
    )

    if normalized_files:
        workspace_path, test_command = create_custom_workspace(
            project_root=project_root,
            run_id=run_id,
            language=normalized_language,
            files=normalized_files,
        )
        initial_state = build_initial_state(
            project_root,
            bug_report,
            str(workspace_path),
            log_path,
            normalized_language,
            run_id=run_id,
            test_command_override=test_command,
            fast_mode=fast_mode,
            execution_mode=execution_mode,
        )
        initial_state["bug_report"] = _augment_bug_report_with_discovery(
            initial_state["bug_report"],
            workspace_path,
            normalized_language,
        )
        initial_state["input_mode"] = "custom"
        return _run_selected_execution_mode(initial_state, execution_mode)

    initial_state = build_initial_state(
        project_root,
        bug_report,
        project_path,
        log_path,
        language,
        run_id=run_id,
        fast_mode=fast_mode,
        execution_mode=execution_mode,
    )
    initial_state["bug_report"] = _augment_bug_report_with_discovery(
        initial_state["bug_report"],
        Path(initial_state["project_path"]),
        initial_state["language"],
    )
    initial_state["input_mode"] = "demo"
    return _run_selected_execution_mode(initial_state, execution_mode)


