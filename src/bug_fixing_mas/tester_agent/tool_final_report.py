from __future__ import annotations

import json
from pathlib import Path


def _load_run_events(state: dict[str, object]) -> list[dict[str, object]]:
    log_path = Path(str(state.get("execution_log_path", "")))
    run_id = state.get("run_id")
    if not log_path.exists() or not run_id:
        return []
    events: list[dict[str, object]] = []
    with log_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            payload = json.loads(line)
            if payload.get("run_id") == run_id:
                events.append(payload)
    return events


def _summarize_observability(state: dict[str, object]) -> dict[str, object]:
    events = _load_run_events(state)
    agent_metrics: dict[str, dict[str, object]] = {}
    total_duration = 0.0
    rollback_count = 0
    supervisor_routing: list[dict[str, object]] = []

    for event in events:
        agent = str(event.get("agent", "unknown"))
        duration = float(event.get("duration_ms", 0.0) or 0.0)
        tool_calls = event.get("tool_calls", []) or []
        total_duration += duration

        if agent == "supervisor":
            output = event.get("output", {}) or {}
            supervisor_routing.append(
                {
                    "stage": output.get("stage", event.get("status", "unknown")),
                    "decision": output.get("decision", "unknown"),
                    "explanation": output.get("explanation", "No explanation recorded."),
                }
            )
            continue

        tool_success = sum(1 for tool in tool_calls if not str(tool.get("tool", "")).startswith("error"))
        agent_metrics[agent] = {
            "duration_ms": round(duration, 2),
            "tool_calls": len(tool_calls),
            "tool_success": tool_success,
            "hallucination_risk": "low" if duration and len(tool_calls) >= 1 else "medium",
            "status": event.get("status", "unknown"),
        }

        if agent == "tester":
            output = event.get("output", {}) or {}
            if bool(output.get("restored_original", False)):
                rollback_count += 1

    return {
        "events": events,
        "agents": agent_metrics,
        "supervisor_routing": supervisor_routing,
        "total_duration_ms": round(total_duration, 2),
        "validation_passed": bool(state.get("test_results", {}).get("passed", False)),
        "rollback_count": rollback_count,
        "final_status": state.get("status", "unknown"),
    }


def _build_architecture_summary(state: dict[str, object]) -> str:
    execution_mode = state.get("execution_mode", "full")
    return (
        "Supervisor routing -> Classifier Agent -> Root Cause Agent -> Fix Generator Agent -> Tester/Report Agent. "
        f"Current execution mode: {execution_mode}. The primary orchestration remains the full LangGraph workflow, "
        "while selective single-agent execution is available for debugging and demonstration."
    )


def _build_testing_summary(state: dict[str, object]) -> list[str]:
    test_results = state.get("test_results", {})
    comparison = test_results.get("comparison", {}) or {}
    lines = [
        f"Validation command: {test_results.get('command', 'unknown')}",
        f"Validation passed: {test_results.get('passed', False)}",
        f"Rollback performed: {test_results.get('restored_original', False)}",
        f"Validator summary: {test_results.get('validator_summary', 'N/A')}",
    ]
    if comparison:
        lines.append(f"Before/after comparison: {comparison.get('summary', 'N/A')}")
    return lines


def _build_limitations() -> list[str]:
    return [
        "The system performs best on localized bugs in small-to-medium codebases rather than large enterprise repositories.",
        "Complex framework-dependent files may still require manual review when project context is incomplete.",
        "Fast Mode uses conservative heuristics and is intended for quicker analysis rather than maximum depth.",
    ]


def _build_future_work() -> list[str]:
    return [
        "Introduce a fully autonomous planner that can dynamically choose additional analysis loops based on validation feedback.",
        "Add deeper language-specific static analysis and richer semantic code understanding for Java and Go.",
        "Extend generated validations into stronger property-based or scenario-based test synthesis.",
    ]


def _build_contribution_table() -> list[tuple[str, str, str]]:
    return [
        ("Member 1", "Classifier Agent", "Bug report parser + classifier evaluation"),
        ("Member 2", "Root Cause Agent", "Code search/static analysis + root-cause evaluation"),
        ("Member 3", "Fix Generator Agent", "Patch/backup/diff tooling + fix-safety evaluation"),
        ("Member 4", "Tester/Report Agent", "Validation/report tooling + rollback/testing evaluation"),
    ]


def _build_markdown_content(state: dict[str, object]) -> str:
    classification = state.get("classification", {})
    root_cause = state.get("root_cause", {})
    patch = state.get("patch", {})
    test_results = state.get("test_results", {})
    observability = _summarize_observability(state)
    agent_metrics = observability.get("agents", {})
    supervisor_routing = observability.get("supervisor_routing", [])

    content = f"""# Bug Fixing MAS Report

## Run Details
- Run ID: {state.get('run_id', 'unknown')}
- Language: {state.get('language', 'unknown')}
- Project Path: {state.get('project_path', 'unknown')}
- Status: {state.get('status', 'unknown')}
- Input Mode: {state.get('input_mode', 'unknown')}
- Execution Mode: {state.get('execution_mode', 'full')}
- Fast Mode: {state.get('fast_mode', False)}
- Total Duration: {observability.get('total_duration_ms', 'N/A')} ms

## Problem Domain
This project implements a locally hosted Multi-Agent System for automated software bug fixing. It classifies bug reports, locates the most likely fault, generates a patch, validates the fix, and produces an auditable report.

## Architecture Summary
{_build_architecture_summary(state)}

## Workflow Diagram
1. Supervisor routing inspects the current stage and confidence.
2. Classifier Agent identifies the bug type and severity.
3. Root Cause Agent searches code, static signals, and evidence.
4. Fix Generator Agent proposes and applies a minimal patch.
5. Tester/Report Agent validates, rolls back if needed, and produces artifacts.

## Bug Report
{state.get('bug_report', '').strip()}

## Agent 1: Classification
- Bug Type: {classification.get('bug_type', 'unknown')}
- Severity: {classification.get('severity', 'unknown')}
- Summary: {classification.get('summary', 'unknown')}
- Likely Modules: {', '.join(classification.get('likely_modules', [])) or 'None identified'}
- Confidence: {classification.get('confidence', 0.0):.2f}
"""

    if "classifier" in agent_metrics:
        classifier_m = agent_metrics["classifier"]
        content += f"- Duration: {classifier_m.get('duration_ms', 'N/A')} ms\n"
        content += f"- Tool Calls: {classifier_m.get('tool_calls', 0)}\n"

    content += f"""

## Agent 2: Root Cause Analysis
- Suspected File: {root_cause.get('suspected_file', 'unknown')}
- Suspected Function: {root_cause.get('suspected_function', 'unknown')}
- Reasoning: {root_cause.get('reasoning', 'unknown')}
- Confidence: {root_cause.get('confidence', 0.0):.2f}
"""

    if "root_cause" in agent_metrics:
        rc_m = agent_metrics["root_cause"]
        content += f"- Duration: {rc_m.get('duration_ms', 'N/A')} ms\n"
        content += f"- Tool Calls: {rc_m.get('tool_calls', 0)}\n"
        content += f"- Tool Success: {rc_m.get('tool_success', 0)}\n"

    content += """

### Evidence
"""
    evidence_lines = root_cause.get("evidence", []) or ["No evidence recorded."]
    content += "\n".join(f"- {line}" for line in evidence_lines)

    content += f"""

## Agent 3: Patch Generation
- Target File: {patch.get('target_file', 'unknown')}
- Backup File: {patch.get('backup_file', 'unknown')}
- Change Summary: {patch.get('change_summary', 'unknown')}
- Confidence: {patch.get('confidence', 0.0):.2f}
"""

    if "fix_generator" in agent_metrics:
        fg_m = agent_metrics["fix_generator"]
        content += f"- Duration: {fg_m.get('duration_ms', 'N/A')} ms\n"
        content += f"- Tool Calls: {fg_m.get('tool_calls', 0)}\n"

    content += f"""

## Agent 4: Validation & Testing
- Test Command: {test_results.get('command', 'unknown')}
- Tests Passed: {test_results.get('passed', False)}
- Rollback Performed: {test_results.get('restored_original', False)}
- Validation Summary: {test_results.get('summary', 'unknown')}
- Validation Confidence: {test_results.get('confidence', 0.0):.2f}
"""

    if "tester" in agent_metrics:
        tester_m = agent_metrics["tester"]
        content += f"- Duration: {tester_m.get('duration_ms', 'N/A')} ms\n"

    content += """

## Testing Summary
"""
    for line in _build_testing_summary(state):
        content += f"- {line}\n"

    content += """

## Observability & Metrics

### Supervisor Routing Decisions
"""
    if supervisor_routing:
        for i, route in enumerate(supervisor_routing, 1):
            content += f"{i}. Stage **{route.get('stage', 'unknown')}** -> **{route.get('decision', 'unknown')}**: {route.get('explanation', 'No explanation recorded.')}\n"
    else:
        content += "No routing decisions recorded.\n"

    content += f"""

### Overall Metrics
- Total Workflow Duration: {observability.get('total_duration_ms', 'N/A')} ms
- Validation Passed: {observability.get('validation_passed', False)}
- Rollback Count: {observability.get('rollback_count', 0)}
- Final Status: {observability.get('final_status', 'unknown')}

## Contribution Mapping
| Team Member | Agent Ownership | Tool / Evaluation Ownership |
| --- | --- | --- |
"""
    for member, agent, ownership in _build_contribution_table():
        content += f"| {member} | {agent} | {ownership} |\n"

    content += """

## Limitations
"""
    for line in _build_limitations():
        content += f"- {line}\n"

    content += """

## Future Work
"""
    for line in _build_future_work():
        content += f"- {line}\n"

    content += f"""

## Final Summary
{state.get('final_summary', '').strip()}

## Recommendation
"""

    status = state.get('status', 'unknown')
    if status == 'tested' and test_results.get('passed'):
        content += "? **PASS** - The patch has been successfully applied and all tests pass. The fix is ready for deployment.\n"
    elif status == 'rolled_back':
        content += "?? **ROLLBACK** - Automatic rollback was performed because validation failed. Manual intervention recommended.\n"
    elif status == 'failed':
        content += "? **FAIL** - The workflow encountered errors and did not produce a validated fix. Investigation required.\n"
    else:
        content += "?? **INCOMPLETE** - The workflow did not complete validation. Check logs for details.\n"

    return content


def write_final_report(output_path: str, state: dict[str, object]) -> str:
    """Write a human-readable markdown report for the current run."""
    report_path = Path(output_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    content = _build_markdown_content(state)
    report_path.write_text(content, encoding="utf-8")
    return str(report_path)


def write_final_report_pdf(output_path: str, markdown_content: str) -> str:
    """Write a professional formatted PDF report using reportlab."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

    pdf_path = Path(output_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=HexColor("#0b3b36"),
        spaceAfter=12,
        alignment=TA_CENTER,
    )

    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=HexColor("#0f766e"),
        spaceAfter=8,
        spaceBefore=12,
        borderColor=HexColor("#d1d5db"),
        borderWidth=0.5,
        borderPadding=6,
    )

    normal_style = ParagraphStyle(
        "CustomNormal",
        parent=styles["Normal"],
        fontSize=10,
        leading=12,
        alignment=TA_JUSTIFY,
        spaceAfter=6,
    )

    for line in markdown_content.strip().split("\n"):
        line = line.rstrip()
        if not line:
            story.append(Spacer(1, 6))
        elif line.startswith("# "):
            story.append(Paragraph(line[2:], title_style))
        elif line.startswith("## "):
            story.append(Paragraph(line[3:], heading_style))
        elif line.startswith("### "):
            story.append(Paragraph(line[4:], ParagraphStyle("Subheading", parent=styles["Heading3"], fontSize=11, textColor=HexColor("#475569"), spaceAfter=6)))
        elif line.startswith("| "):
            story.append(Paragraph(line.replace("|", "&nbsp;&nbsp;|&nbsp;&nbsp;"), normal_style))
        elif line.startswith("- "):
            story.append(Paragraph(f"• {line[2:]}", normal_style))
        else:
            story.append(Paragraph(line, normal_style))

    doc.build(story)
    return str(pdf_path)

