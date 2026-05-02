from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(slots=True)
class ParsedBugReport:
    """Normalized bug report details used by the classifier agent."""

    title: str
    body: str
    error_keywords: list[str]


def parse_bug_report(report_text: str) -> ParsedBugReport:
    """Extract the title, full body, and a compact keyword list from a bug report."""
    lines = [line.strip() for line in report_text.splitlines() if line.strip()]
    title = lines[0] if lines else "Untitled bug report"
    keywords = sorted(set(re.findall(r"[A-Za-z_]{4,}", report_text.lower())))
    return ParsedBugReport(title=title, body=report_text.strip(), error_keywords=keywords[:15])
