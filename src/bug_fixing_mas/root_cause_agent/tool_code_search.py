from __future__ import annotations

import ast
import py_compile
import re
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, TypedDict


class SearchMatch(TypedDict):
    file: str
    term: str
    line_number: int
    snippet: str
    is_test_file: bool
    score: int
    context: list[str]


class StaticSignal(TypedDict):
    tool: str
    file: str
    passed: bool
    summary: str


TERM_PATTERNS = {
    "lock": re.compile(r"\block\b|\bmutex\b|\bsynchronized\b"),
    "thread": re.compile(r"\bthread\w*\b|\bgoroutine\b"),
    "error": re.compile(r"\berror\b|\bexception\b|\bonstatus\b|\bthrow\b|\bpanic\b"),
    "divide": re.compile(r"\bdivide\b|/|zerodivision|arithmeticexception"),
    "validation": re.compile(r"\bvalidate\b|\bvalueerror\b|\billegalargumentexception\b|\brequired\b|\bnull\b"),
}

TEST_FILE_PATTERNS = (
    re.compile(r"(^|[\\/])test_[^\\/]+\.py$", re.IGNORECASE),
    re.compile(r"(^|[\\/]).+_test\.py$", re.IGNORECASE),
    re.compile(r"(^|[\\/]).+\.test\.js$", re.IGNORECASE),
    re.compile(r"(^|[\\/]).+\.spec\.js$", re.IGNORECASE),
    re.compile(r"(^|[\\/]).*Test\.java$", re.IGNORECASE),
    re.compile(r"(^|[\\/]).+_test\.go$", re.IGNORECASE),
)


def _matches_term(lowered: str, term: str) -> bool:
    normalized = term.lower().strip()
    if not normalized:
        return False
    pattern = TERM_PATTERNS.get(normalized)
    if pattern is not None:
        return bool(pattern.search(lowered))
    if len(normalized) <= 3:
        return normalized in lowered
    return re.search(rf"\b{re.escape(normalized)}\b", lowered) is not None


def _is_test_file(path: Path) -> bool:
    path_text = str(path)
    return any(pattern.search(path_text) for pattern in TEST_FILE_PATTERNS)


def _file_priority(path: Path) -> int:
    return 0 if _is_test_file(path) else 1


def _term_weight(term: str, snippet: str) -> int:
    normalized = term.lower().strip()
    lowered = snippet.lower()
    score = 1
    if normalized in {"divide", "zero", "arithmeticerror"} and ("divide" in lowered or "return 0" in lowered or "== 0" in lowered):
        score += 4
    if normalized in {"error", "exception", "onstatus"} and any(token in lowered for token in ["exception", "onstatus", "throw", "catch", "error"]):
        score += 3
    if normalized in {"validation", "valueerror", "illegalargumentexception"} and any(token in lowered for token in ["valueerror", "illegalargumentexception", "validate", "required"]):
        score += 3
    if normalized in {"lock", "thread", "concurrency", "mutex", "atomic", "shared state"} and any(token in lowered for token in ["lock", "thread", "mutex", "atomic", "synchronized"]):
        score += 3
    return score


def _extract_context_window(lines: list[str], line_number: int, radius: int = 2) -> list[str]:
    start = max(0, line_number - 1 - radius)
    end = min(len(lines), line_number + radius)
    return [lines[index].rstrip() for index in range(start, end)]


def _extract_python_functions(file_path: str) -> dict[str, int]:
    """
    Parse Python AST to extract function names and their line numbers.
    Used for prioritizing matches in function definitions (real-world robustness).
    
    Returns: dict mapping function names to their line numbers.
    """
    try:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError):
        return {}
    
    functions = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions[node.name] = node.lineno
    return functions


def _calculate_match_priority(file_path: str, line_number: int, term: str, snippet: str, language: str) -> int:
    """
    Advanced scoring: prioritizes matches in function definitions, control flow junctions, and error paths.
    Real-world robustness: matches closer to the actual error site score higher.
    """
    base_priority = _file_priority(file_path) * 10
    term_weight = _term_weight(term, snippet)
    
    # Boost for being in an error/exception context
    error_indicators = ["raise", "throw", "panic", "return", "assert", "if", "try", "catch"]
    for indicator in error_indicators:
        if indicator in snippet.lower():
            term_weight += 2
    
    # Boost for lines with control flow (dividing point in bugs)
    if any(kw in snippet.lower() for kw in ["if", "else", "while", "for", "try", "catch"]):
        term_weight += 1
    
    # For Python: boost if in a function definition
    if language == "python":
        functions = _extract_python_functions(file_path)
        for func_name, func_line in functions.items():
            if func_line <= line_number < func_line + 50:  # Within 50 lines of function def
                term_weight += 3
                break
    
    return base_priority + term_weight


def search_source_files(
    project_path: str,
    search_terms: Iterable[str],
    source_extensions: Iterable[str],
    language: str = "python",
) -> list[SearchMatch]:
    """Search source files, rank likely matches, and return snippets with nearby context.
    
    Real-world robustness improvements:
    - Uses AST analysis for Python to find function boundaries
    - Prioritizes matches in control flow junctions and error paths
    - Scores based on proximity to function definitions
    - Extracts richer context windows
    """
    base_path = Path(project_path)
    terms = [term.lower() for term in search_terms if term and term.strip()]
    allowed_suffixes = {suffix.lower() for suffix in source_extensions}
    matches: list[SearchMatch] = []

    for file_path in base_path.rglob("*"):
        if not file_path.is_file() or file_path.suffix.lower() not in allowed_suffixes:
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        lines = content.splitlines()
        for line_number, line in enumerate(lines, start=1):
            lowered = line.lower()
            for term in terms:
                if _matches_term(lowered, term):
                    # Use advanced priority calculation
                    score = _calculate_match_priority(str(file_path), line_number, term, line.strip(), language)
                    matches.append(
                        {
                            "file": str(file_path),
                            "term": term,
                            "line_number": line_number,
                            "snippet": line.strip(),
                            "is_test_file": _is_test_file(file_path),
                            "score": score,
                            "context": _extract_context_window(lines, line_number),
                        }
                    )
                    break

    matches.sort(
        key=lambda item: (
            -int(item.get("score", 0)),
            bool(item.get("is_test_file", False)),
            str(item.get("file", "")),
            int(item.get("line_number", 0)),
        )
    )
    return matches


def scan_concurrency_risks(project_path: str, source_extensions: Iterable[str]) -> list[dict[str, str | int | bool]]:
    """Find lightweight concurrency-risk indicators such as threads, locks, and shared-state updates."""
    base_path = Path(project_path)
    allowed_suffixes = {suffix.lower() for suffix in source_extensions}
    risk_terms = [
        re.compile(r"\bthreading\b|\bthread\w*\b|\bgoroutine\b"),
        re.compile(r"\block\b|\bmutex\b|\bsynchronized\b|\batomic\b"),
        re.compile(r"time\.sleep|\.start\(\)|\.join\(\)"),
        re.compile(r"shared|self\.value\s*=|value\s*=\s*current\s*\+\s*1"),
    ]
    findings: list[SearchMatch] = []

    for file_path in base_path.rglob("*"):
        if not file_path.is_file() or file_path.suffix.lower() not in allowed_suffixes:
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(content.splitlines(), start=1):
            lowered = line.lower()
            if any(pattern.search(lowered) for pattern in risk_terms):
                findings.append(
                    {
                        "file": str(file_path),
                        "term": "concurrency-risk",
                        "line_number": line_number,
                        "snippet": line.strip(),
                        "is_test_file": _is_test_file(file_path),
                        "score": 12 if not _is_test_file(file_path) else 4,
                    }
                )
    findings.sort(key=lambda item: (-int(item["score"]), bool(item["is_test_file"]), str(item["file"]), int(item["line_number"])))
    return findings


def extract_function_context(file_path: str, function_name: str, radius: int = 18) -> str:
    """Extract a compact function-centered context window for LLM grounding."""
    path = Path(file_path)
    if not path.exists():
        return ""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return ""
    patterns = [
        re.compile(rf"\bdef\s+{re.escape(function_name)}\b"),
        re.compile(rf"\bfunction\s+{re.escape(function_name)}\b"),
        re.compile(rf"\bfunc\s+{re.escape(function_name)}\b"),
        re.compile(rf"\b{re.escape(function_name)}\s*\("),
    ]
    for index, line in enumerate(lines):
        lowered = line.lower()
        if any(pattern.search(lowered) for pattern in patterns):
            start = max(0, index - 3)
            end = min(len(lines), index + radius)
            return "\n".join(lines[start:end])
    return "\n".join(lines[: min(len(lines), radius)])


def extract_nearby_code(file_path: str, line_number: int, radius: int = 4) -> str:
    """Extract nearby code around a matched evidence line."""
    path = Path(file_path)
    if not path.exists():
        return ""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return ""
    start = max(0, line_number - 1 - radius)
    end = min(len(lines), line_number + radius)
    return "\n".join(lines[start:end])


def collect_static_signals(project_path: str, language: str, source_extensions: Iterable[str]) -> list[dict[str, str | bool]]:
    """Run lightweight language-specific static checks to guide identification before LLM reasoning."""
    base_path = Path(project_path)
    files = [path for path in sorted(base_path.rglob("*")) if path.is_file() and path.suffix.lower() in {suffix.lower() for suffix in source_extensions}]
    findings: list[StaticSignal] = []

    for file_path in files[:12]:
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        lowered = content.lower()

        if language == "python":
            try:
                ast.parse(content)
                findings.append({"tool": "ast", "file": str(file_path), "passed": True, "summary": "AST parse passed."})
            except SyntaxError as exc:
                findings.append({"tool": "ast", "file": str(file_path), "passed": False, "summary": f"AST parse failed: {exc.msg} at line {exc.lineno}."})
            try:
                py_compile.compile(str(file_path), doraise=True)
                findings.append({"tool": "py_compile", "file": str(file_path), "passed": True, "summary": "Bytecode compile passed."})
            except py_compile.PyCompileError as exc:
                findings.append({"tool": "py_compile", "file": str(file_path), "passed": False, "summary": str(exc).strip()})
            if shutil.which("ruff"):
                completed = subprocess.run(["ruff", "check", str(file_path)], cwd=base_path, capture_output=True, text=True, check=False)
                findings.append({"tool": "ruff", "file": str(file_path), "passed": completed.returncode == 0, "summary": (completed.stdout or completed.stderr or "ruff check completed").strip()[:300]})

        if language == "java":
            if "return 0;" in lowered and "if (b == 0)" in lowered:
                findings.append({"tool": "pattern", "file": str(file_path), "passed": False, "summary": "Detected divide-by-zero branch returning 0."})
            if ".onstatus(" in lowered and ".map(" in lowered and "exception" in lowered:
                findings.append({"tool": "pattern", "file": str(file_path), "passed": False, "summary": "Detected reactive error propagation anti-pattern using onStatus + map(Exception)."})
            if "catch (exception" in lowered and "throw" not in lowered:
                findings.append({"tool": "pattern", "file": str(file_path), "passed": False, "summary": "Detected broad catch(Exception) without rethrow."})

        if language == "javascript":
            if shutil.which("node"):
                completed = subprocess.run(["node", "--check", str(file_path)], cwd=base_path, capture_output=True, text=True, check=False)
                findings.append({"tool": "node --check", "file": str(file_path), "passed": completed.returncode == 0, "summary": (completed.stderr or "Syntax check passed.").strip()[:300]})
            if "return 0;" in lowered and "if (b === 0)" in lowered:
                findings.append({"tool": "pattern", "file": str(file_path), "passed": False, "summary": "Detected divide-by-zero branch returning 0."})

        if language == "go":
            if shutil.which("gofmt"):
                completed = subprocess.run(["gofmt", "-l", str(file_path)], cwd=base_path, capture_output=True, text=True, check=False)
                needs_formatting = bool(completed.stdout.strip())
                if completed.returncode != 0:
                    summary = (completed.stderr or "gofmt check failed.").strip()[:300]
                    passed = False
                elif needs_formatting:
                    summary = "gofmt style differences detected (non-mutating check)."
                    passed = False
                else:
                    summary = "gofmt style check passed (non-mutating check)."
                    passed = True
                findings.append({"tool": "gofmt", "file": str(file_path), "passed": passed, "summary": summary})
            if "return 0" in lowered and "if b == 0" in lowered:
                findings.append({"tool": "pattern", "file": str(file_path), "passed": False, "summary": "Detected divide-by-zero branch returning 0."})

        if any(token in lowered for token in ["return true", "return false"]):
            findings.append({"tool": "pattern", "file": str(file_path), "passed": False, "summary": "Detected constant boolean return that may indicate wrong-return logic."})
        if any(token in lowered for token in ["return age", "return value", "return input"]) and any(token in lowered for token in ["< 0", "negative", "invalid"]):
            findings.append({"tool": "pattern", "file": str(file_path), "passed": False, "summary": "Detected likely missing validation or invalid-input handling."})

    return findings[:24]
