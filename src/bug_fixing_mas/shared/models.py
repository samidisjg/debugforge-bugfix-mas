from __future__ import annotations

from pydantic import BaseModel, Field


class ClassificationResult(BaseModel):
    """Structured output for the bug classifier agent."""

    bug_type: str = Field(description="Main category such as logic, runtime, validation, concurrency, or test failure.")
    severity: str = Field(description="Impact level such as low, medium, or high.")
    summary: str = Field(description="Short bug summary.")
    likely_modules: list[str] = Field(default_factory=list, description="Likely file or module names.")
    confidence: float = Field(default=0.5, description="Confidence score from 0.0 to 1.0.")


class RootCauseResult(BaseModel):
    """Structured output for the root cause agent."""

    suspected_file: str = Field(description="Primary file that contains the defect.")
    suspected_function: str = Field(description="Function or class likely responsible.")
    evidence: list[str] = Field(default_factory=list, description="Concrete evidence from search results.")
    reasoning: str = Field(description="Why this is the likely root cause.")
    confidence: float = Field(default=0.5, description="Confidence score from 0.0 to 1.0.")


class PatchResult(BaseModel):
    """Structured output for the fix generator agent."""

    target_file: str = Field(description="File that must be updated.")
    new_code: str = Field(description="Full replacement code for the target file.")
    change_summary: str = Field(description="Short summary of the patch.")
    confidence: float = Field(default=0.5, description="Confidence score from 0.0 to 1.0.")


class TestResult(BaseModel):
    """Structured output for the tester agent."""

    passed: bool = Field(description="True when validation passed.")
    command: str = Field(description="Executed validation command.")
    stdout: str = Field(description="Captured standard output.")
    stderr: str = Field(description="Captured standard error.")
    summary: str = Field(description="Human-readable test summary.")
    confidence: float = Field(default=0.5, description="Confidence score from 0.0 to 1.0.")
