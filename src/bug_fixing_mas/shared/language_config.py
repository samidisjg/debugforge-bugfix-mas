from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class LanguageConfig:
    """Language-specific project configuration."""

    name: str
    source_extensions: tuple[str, ...]
    code_fence: str


LANGUAGE_CONFIGS: dict[str, LanguageConfig] = {
    "python": LanguageConfig(name="python", source_extensions=(".py",), code_fence="python"),
    "javascript": LanguageConfig(name="javascript", source_extensions=(".js", ".mjs", ".cjs"), code_fence="javascript"),
    "java": LanguageConfig(name="java", source_extensions=(".java",), code_fence="java"),
    "go": LanguageConfig(name="go", source_extensions=(".go",), code_fence="go"),
}


IS_WINDOWS = os.name == "nt"


def detect_project_language(project_path: str) -> str:
    """Detect the dominant language of a project from common files and extensions."""
    base_path = Path(project_path)
    if (base_path / "pyproject.toml").exists() or list(base_path.rglob("*.py")):
        return "python"
    if (base_path / "package.json").exists() or list(base_path.rglob("*.js")):
        return "javascript"
    if (base_path / "pom.xml").exists() or (base_path / "build.gradle").exists() or list(base_path.rglob("*.java")):
        return "java"
    if (base_path / "go.mod").exists() or list(base_path.rglob("*.go")):
        return "go"
    return "python"


def get_language_config(language: str) -> LanguageConfig:
    """Return normalized language configuration, defaulting to Python."""
    return LANGUAGE_CONFIGS.get(language.lower(), LANGUAGE_CONFIGS["python"])


def determine_test_command(project_path: str, language: str) -> list[str]:
    """Return the best-effort local test command for a supported language."""
    base_path = Path(project_path)
    normalized = language.lower()
    if normalized == "python":
        return ["python", "-m", "pytest", "-q"]
    if normalized == "javascript":
        npm_bin = "npm.cmd" if IS_WINDOWS else "npm"
        return [npm_bin, "test", "--", "--runInBand"]
    if normalized == "java":
        if (base_path / "pom.xml").exists():
            mvn_bin = "mvn.cmd" if IS_WINDOWS else "mvn"
            return [mvn_bin, "test", "-q"]
        if (base_path / "gradlew").exists() or (base_path / "gradlew.bat").exists():
            return ["gradlew.bat" if IS_WINDOWS else "./gradlew", "test"]
        mvn_bin = "mvn.cmd" if IS_WINDOWS else "mvn"
        return [mvn_bin, "test", "-q"]
    if normalized == "go":
        return ["go", "test", "./..."]
    return ["python", "-m", "pytest", "-q"]
