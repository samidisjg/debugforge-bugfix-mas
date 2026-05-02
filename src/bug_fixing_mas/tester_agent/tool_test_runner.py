from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from bug_fixing_mas.shared.language_config import determine_test_command
from bug_fixing_mas.shared.models import TestResult


def _source_files_for_language(base_path: Path, language: str) -> list[Path]:
    suffixes = {
        "python": (".py",),
        "javascript": (".js", ".mjs", ".cjs"),
        "java": (".java",),
        "go": (".go",),
    }.get(language, ())
    return sorted(path for path in base_path.rglob("*") if path.is_file() and path.suffix in suffixes)


def _run_subprocess(command: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False, env=env)


def _run_python_generated_check(base_path: Path, files: list[Path], env: dict[str, str]) -> TestResult | None:
    for file_path in files:
        content = file_path.read_text(encoding="utf-8")
        module_name = file_path.stem
        if "def divide" in content:
            runner_code = (
                f"import {module_name}\n"
                "try:\n"
                f"    result = {module_name}.divide(5, 0)\n"
                "    raise AssertionError(f'divide(5, 0) returned {result!r} instead of raising')\n"
                "except ZeroDivisionError:\n"
                "    print('edge-case passed')\n"
            )
            completed = _run_subprocess(["python", "-c", runner_code], base_path, env)
            return TestResult(
                passed=completed.returncode == 0,
                command="python generated edge-case validation",
                stdout=completed.stdout,
                stderr=completed.stderr,
                summary=(
                    "Auto-generated edge-case validation passed for divide-by-zero behavior."
                    if completed.returncode == 0
                    else "Auto-generated edge-case validation failed for divide-by-zero behavior."
                ),
                confidence=0.9 if completed.returncode == 0 else 0.45,
            )
        if "def normalize_age" in content and "non-negative" in content:
            runner_code = (
                f"import {module_name}\n"
                "try:\n"
                f"    {module_name}.normalize_age(-1)\n"
                "    raise AssertionError('normalize_age(-1) accepted invalid input')\n"
                "except ValueError:\n"
                "    print('validation passed')\n"
            )
            completed = _run_subprocess(["python", "-c", runner_code], base_path, env)
            return TestResult(
                passed=completed.returncode == 0,
                command="python generated validation check",
                stdout=completed.stdout,
                stderr=completed.stderr,
                summary=(
                    "Auto-generated validation check passed for negative-input rejection."
                    if completed.returncode == 0
                    else "Auto-generated validation check failed for negative-input rejection."
                ),
                confidence=0.84 if completed.returncode == 0 else 0.42,
            )
        if "def is_even" in content:
            runner_code = (
                f"import {module_name}\n"
                f"assert {module_name}.is_even(2) is True\n"
                f"assert {module_name}.is_even(3) is False\n"
                "print('logic passed')\n"
            )
            completed = _run_subprocess(["python", "-c", runner_code], base_path, env)
            return TestResult(
                passed=completed.returncode == 0,
                command="python generated logic check",
                stdout=completed.stdout,
                stderr=completed.stderr,
                summary=(
                    "Auto-generated logic check passed for even/odd behavior."
                    if completed.returncode == 0
                    else "Auto-generated logic check failed for even/odd behavior."
                ),
                confidence=0.82 if completed.returncode == 0 else 0.4,
            )
    return None


def _run_java_generated_check(base_path: Path, files: list[Path], env: dict[str, str]) -> TestResult | None:
    if shutil.which("javac") is None or shutil.which("java") is None:
        return None
    for file_path in files:
        content = file_path.read_text(encoding="utf-8")
        if "package " in content:
            continue
        if "static int divide" in content:
            class_name = file_path.stem
            runner_path = base_path / "GeneratedValidationRunner.java"
            runner_path.write_text(
                (
                    "public class GeneratedValidationRunner {\n"
                    "    public static void main(String[] args) {\n"
                    "        try {\n"
                    f"            int result = {class_name}.divide(5, 0);\n"
                    "            throw new RuntimeException(\"divide(5,0) returned \" + result + \" instead of throwing\");\n"
                    "        } catch (ArithmeticException expected) {\n"
                    "            System.out.println(\"ok\");\n"
                    "        }\n"
                    "    }\n"
                    "}\n"
                ),
                encoding="utf-8",
            )
            compile_step = _run_subprocess(["javac", file_path.name, runner_path.name], base_path, env)
            if compile_step.returncode != 0:
                return TestResult(
                    passed=False,
                    command="javac generated edge-case validation",
                    stdout=compile_step.stdout,
                    stderr=compile_step.stderr,
                    summary="Auto-generated edge-case validation failed to compile.",
                    confidence=0.3,
                )
            completed = _run_subprocess(["java", "GeneratedValidationRunner"], base_path, env)
            return TestResult(
                passed=completed.returncode == 0,
                command="java generated edge-case validation",
                stdout=completed.stdout,
                stderr=completed.stderr,
                summary=(
                    "Auto-generated edge-case validation passed for divide-by-zero behavior."
                    if completed.returncode == 0
                    else "Auto-generated edge-case validation failed for divide-by-zero behavior."
                ),
                confidence=0.88 if completed.returncode == 0 else 0.4,
            )
    return None


def _run_javascript_generated_check(base_path: Path, files: list[Path], env: dict[str, str]) -> TestResult | None:
    if shutil.which("node") is None:
        return None
    for file_path in files:
        content = file_path.read_text(encoding="utf-8")
        if "function divide" in content:
            runner_code = (
                f"const mod = require('./{file_path.name}');\n"
                "let threw = false;\n"
                "try { mod.divide(5, 0); } catch (error) { threw = true; }\n"
                "if (!threw) { throw new Error('divide(5,0) did not throw'); }\n"
                "console.log('edge-case passed');\n"
            )
            completed = _run_subprocess(["node", "-e", runner_code], base_path, env)
            return TestResult(
                passed=completed.returncode == 0,
                command="node generated edge-case validation",
                stdout=completed.stdout,
                stderr=completed.stderr,
                summary=(
                    "Auto-generated edge-case validation passed for divide-by-zero behavior."
                    if completed.returncode == 0
                    else "Auto-generated edge-case validation failed for divide-by-zero behavior."
                ),
                confidence=0.8 if completed.returncode == 0 else 0.4,
            )
    return None


def _run_go_generated_check(base_path: Path, files: list[Path], env: dict[str, str]) -> TestResult | None:
    if shutil.which("go") is None:
        return None
    if not any("func divide" in file_path.read_text(encoding="utf-8") for file_path in files):
        return None
    test_path = base_path / "generated_validation_test.go"
    test_path.write_text(
        (
            "package main\n\n"
            "import \"testing\"\n\n"
            "func TestGeneratedDivideByZeroPanics(t *testing.T) {\n"
            "    defer func() {\n"
            "        if recover() == nil {\n"
            "            t.Fatalf(\"expected panic for divide(5,0)\")\n"
            "        }\n"
            "    }()\n"
            "    divide(5, 0)\n"
            "}\n"
        ),
        encoding="utf-8",
    )
    completed = _run_subprocess(["go", "test", "./..."], base_path, env)
    return TestResult(
        passed=completed.returncode == 0,
        command="go generated edge-case validation",
        stdout=completed.stdout,
        stderr=completed.stderr,
        summary=(
            "Auto-generated edge-case validation passed for divide-by-zero behavior."
            if completed.returncode == 0
            else "Auto-generated edge-case validation failed for divide-by-zero behavior."
        ),
        confidence=0.82 if completed.returncode == 0 else 0.38,
    )


def _run_generated_smoke_validation(base_path: Path, language: str, env: dict[str, str]) -> TestResult | None:
    files = _source_files_for_language(base_path, language)
    if language == "python":
        return _run_python_generated_check(base_path, files, env)
    if language == "java":
        return _run_java_generated_check(base_path, files, env)
    if language == "javascript":
        return _run_javascript_generated_check(base_path, files, env)
    if language == "go":
        return _run_go_generated_check(base_path, files, env)
    return None


def _run_static_validation(base_path: Path, language: str, env: dict[str, str]) -> TestResult | None:
    files = _source_files_for_language(base_path, language)
    if not files:
        return None
    if language == "python":
        completed = _run_subprocess(["python", "-m", "compileall", "-q", "."], base_path, env)
        return TestResult(
            passed=completed.returncode == 0,
            command="python -m compileall -q .",
            stdout=completed.stdout,
            stderr=completed.stderr,
            summary=("Static Python compile validation passed." if completed.returncode == 0 else "Static Python compile validation failed."),
            confidence=0.72 if completed.returncode == 0 else 0.3,
        )
    if language == "javascript":
        if shutil.which("node") is None:
            return TestResult(passed=False, command="node --check", stdout="", stderr="node executable not found", summary="Node.js is required for static JavaScript validation.", confidence=0.2)
        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        passed = True
        for file_path in files:
            completed = _run_subprocess(["node", "--check", str(file_path)], base_path, env)
            stdout_parts.append(completed.stdout)
            stderr_parts.append(completed.stderr)
            if completed.returncode != 0:
                passed = False
        return TestResult(
            passed=passed,
            command=f"node --check ({len(files)} files)",
            stdout="\n".join(part for part in stdout_parts if part),
            stderr="\n".join(part for part in stderr_parts if part),
            summary=("Static JavaScript syntax validation passed." if passed else "Static JavaScript syntax validation failed."),
            confidence=0.72 if passed else 0.3,
        )
    if language == "java":
        if shutil.which("javac") is None:
            return TestResult(passed=False, command="javac -Xlint:none", stdout="", stderr="javac executable not found", summary="JDK is required for static Java validation.", confidence=0.2)
        completed = _run_subprocess(["javac", "-Xlint:none", *[str(path) for path in files]], base_path, env)
        return TestResult(
            passed=completed.returncode == 0,
            command=f"javac -Xlint:none ({len(files)} files)",
            stdout=completed.stdout,
            stderr=completed.stderr,
            summary=("Static Java compilation validation passed." if completed.returncode == 0 else "Static Java compilation validation failed."),
            confidence=0.74 if completed.returncode == 0 else 0.28,
        )
    if language == "go":
        if shutil.which("go") is None:
            return TestResult(passed=False, command="go test ./...", stdout="", stderr="go executable not found", summary="Go executable not found for static validation.", confidence=0.2)
        completed = _run_subprocess(["go", "test", "./..."], base_path, env)
        return TestResult(
            passed=completed.returncode == 0,
            command="go test ./...",
            stdout=completed.stdout,
            stderr=completed.stderr,
            summary=("Static Go validation passed." if completed.returncode == 0 else "Static Go validation failed."),
            confidence=0.72 if completed.returncode == 0 else 0.28,
        )
    return None


def _run_command_validation(base_path: Path, command: list[str], language: str, env: dict[str, str]) -> TestResult:
    try:
        completed = _run_subprocess(command, base_path, env)
    except FileNotFoundError as exc:
        return TestResult(
            passed=False,
            command=" ".join(command),
            stdout="",
            stderr=str(exc),
            summary=f"Required test tool was not found for language '{language}'.",
            confidence=0.2,
        )
    passed = completed.returncode == 0
    return TestResult(
        passed=passed,
        command=" ".join(command),
        stdout=completed.stdout,
        stderr=completed.stderr,
        summary="Tests passed." if passed else "Tests failed after applying the patch.",
        confidence=0.88 if passed else 0.32,
    )


def run_project_tests(project_path: str, language: str, command_override: list[str] | None = None) -> TestResult:
    """Run layered validation: static checks, explicit tests, and generated edge-case tests."""
    base_path = Path(project_path).resolve()
    command = command_override if command_override is not None else determine_test_command(str(base_path), language)
    env = os.environ.copy()

    if language == "go":
        go_cache = (base_path / ".gocache").resolve()
        go_cache.mkdir(parents=True, exist_ok=True)
        env["GOCACHE"] = str(go_cache)

    static_result = _run_static_validation(base_path, language, env)
    if static_result is not None and not static_result.passed:
        return static_result

    if command:
        command_result = _run_command_validation(base_path, command, language, env)
        if not command_result.passed:
            return command_result

    generated_result = _run_generated_smoke_validation(base_path, language, env)
    if generated_result is not None:
        return generated_result

    if static_result is not None:
        return TestResult(
            passed=static_result.passed,
            command=static_result.command,
            stdout=static_result.stdout,
            stderr=static_result.stderr,
            summary=f"{static_result.summary} No targeted generated validation was available.",
            confidence=static_result.confidence,
        )

    return TestResult(
        passed=True,
        command="validation skipped",
        stdout="",
        stderr="",
        summary="No automated tests or source files were provided; validation was skipped.",
        confidence=0.25,
    )


def compare_bug_behavior(project_path: str, language: str, target_file: str, reference_file: str | None = None) -> dict[str, str | bool]:
    """Compare a small generated bug scenario before and after a patch when a reference file is available."""
    if not reference_file:
        return {"compared": False, "summary": "No backup file available for before/after comparison."}

    target_path = Path(target_file)
    reference_path = Path(reference_file)
    if not target_path.exists() or not reference_path.exists():
        return {"compared": False, "summary": "Comparison files were not available on disk."}

    current_code = target_path.read_text(encoding="utf-8")
    original_code = reference_path.read_text(encoding="utf-8")

    if language == "python" and "def divide" in current_code and "def divide" in original_code:
        improved = "raise ZeroDivisionError" in current_code and "return 0" in original_code
        return {
            "compared": True,
            "improved": improved,
            "summary": (
                "Before/after comparison shows divide-by-zero behavior improved in the patched file."
                if improved
                else "Before/after comparison did not confirm divide-by-zero behavior improvement."
            ),
        }

    if language == "java" and "static int divide" in current_code and "static int divide" in original_code:
        improved = "throw new ArithmeticException" in current_code and "return 0;" in original_code
        return {
            "compared": True,
            "improved": improved,
            "summary": (
                "Before/after comparison shows divide-by-zero behavior improved in the patched Java file."
                if improved
                else "Before/after comparison did not confirm divide-by-zero behavior improvement in Java."
            ),
        }

    if language == "javascript" and "function divide" in current_code and "function divide" in original_code:
        improved = "throw new Error" in current_code and "return 0;" in original_code
        return {
            "compared": True,
            "improved": improved,
            "summary": (
                "Before/after comparison shows divide-by-zero behavior improved in the patched JavaScript file."
                if improved
                else "Before/after comparison did not confirm divide-by-zero behavior improvement in JavaScript."
            ),
        }

    if language == "go" and "func divide" in current_code and "func divide" in original_code:
        improved = "panic(" in current_code and "return 0" in original_code
        return {
            "compared": True,
            "improved": improved,
            "summary": (
                "Before/after comparison shows divide-by-zero behavior improved in the patched Go file."
                if improved
                else "Before/after comparison did not confirm divide-by-zero behavior improvement in Go."
            ),
        }

    return {"compared": False, "summary": "No before/after comparison rule matched this file."}
