from __future__ import annotations

from time import perf_counter

from langchain_ollama import ChatOllama

from bug_fixing_mas.classifier_agent.tool_bug_report_parser import parse_bug_report
from bug_fixing_mas.shared.logging_utils import append_jsonl_log
from bug_fixing_mas.shared.models import ClassificationResult
from bug_fixing_mas.shared.prompt_loader import load_prompt
from bug_fixing_mas.shared.state import BugFixState
from bug_fixing_mas.shared.state_validators import ensure_state_is_valid_for_agent


MODEL_NAME = "llama3.1:8b"
PROMPT_FILE = "classifier_prompt.md"


CONCURRENCY_TERMS = ["race", "thread", "deadlock", "mutex", "lock", "concurrency", "shared state", "atomic"]


def _heuristic_classification(report_body: str) -> dict[str, object] | None:
    lowered = report_body.lower()
    if "divide-by-zero branch returns 0" in lowered:
        return {
            "bug_type": "ArithmeticError",
            "severity": "Medium",
            "summary": "Detected a divide-by-zero branch that returns 0 instead of failing safely.",
            "likely_modules": [],
            "confidence": 0.92,
        }
    if "reactive onstatus with map(exception) may not propagate errors correctly" in lowered:
        return {
            "bug_type": "Error Propagation",
            "severity": "Medium",
            "summary": "Reactive onStatus error mapping may not propagate failures correctly.",
            "likely_modules": [],
            "confidence": 0.86,
        }
    if "catch(exception) block without rethrow can mask failures" in lowered:
        return {
            "bug_type": "Error Handling",
            "severity": "Medium",
            "summary": "A broad catch block appears to swallow failures without proper propagation.",
            "likely_modules": [],
            "confidence": 0.82,
        }
    if "divide by zero" in lowered:
        return {
            "bug_type": "ArithmeticError",
            "severity": "Medium",
            "summary": "Bug report indicates divide-by-zero behavior.",
            "likely_modules": [],
            "confidence": 0.74,
        }
    if any(term in lowered for term in CONCURRENCY_TERMS):
        return {
            "bug_type": "Concurrency Bug",
            "severity": "High",
            "summary": "Bug report suggests a race, locking, or shared-state concurrency issue.",
            "likely_modules": [],
            "confidence": 0.76,
        }
    return None


def _fast_classification(report_body: str, static_signals: list[dict[str, object]]) -> dict[str, object]:
    signal_text = " ".join(str(signal.get("summary", "")).lower() for signal in static_signals)
    combined = f"{report_body.lower()} {signal_text}"
    if any(term in combined for term in ["divide-by-zero", "divide by zero", "arithmeticexception", "zerodivisionerror"]):
        return {
            "bug_type": "ArithmeticError",
            "severity": "Medium",
            "summary": "Fast mode detected divide-by-zero style arithmetic behavior.",
            "likely_modules": [],
            "confidence": 0.8,
        }
    if any(term in combined for term in ["validation", "non-negative", "invalid input", "valueerror", "illegalargumentexception"]):
        return {
            "bug_type": "Validation Bug",
            "severity": "Medium",
            "summary": "Fast mode detected missing or incorrect input validation.",
            "likely_modules": [],
            "confidence": 0.72,
        }
    if any(term in combined for term in ["wrong return", "incorrect result", "logic", "return true"]):
        return {
            "bug_type": "Logic Bug",
            "severity": "Medium",
            "summary": "Fast mode detected likely incorrect return or branching logic.",
            "likely_modules": [],
            "confidence": 0.68,
        }
    if any(term in combined for term in ["onstatus", "catch(exception)", "error propagation", "exception"]):
        return {
            "bug_type": "Error Propagation",
            "severity": "Medium",
            "summary": "Fast mode detected exception handling or propagation risk.",
            "likely_modules": [],
            "confidence": 0.7,
        }
    if any(term in combined for term in CONCURRENCY_TERMS):
        return {
            "bug_type": "Concurrency Bug",
            "severity": "High",
            "summary": "Fast mode detected shared-state concurrency risk.",
            "likely_modules": [],
            "confidence": 0.7,
        }
    return {
        "bug_type": "Behavioral Bug",
        "severity": "Medium",
        "summary": "Fast mode found a likely localized bug but needs more explicit detail for a narrower label.",
        "likely_modules": [],
        "confidence": 0.55,
    }


def classifier_agent(state: BugFixState) -> BugFixState:
    """Classify the incoming bug report."""
    ensure_state_is_valid_for_agent("classifier", state)
    started_at = perf_counter()
    parsed_report = parse_bug_report(state["bug_report"])
    concurrency_hint = any(term in parsed_report.body.lower() for term in CONCURRENCY_TERMS)
    heuristic = _heuristic_classification(parsed_report.body)
    prompt_template = load_prompt(PROMPT_FILE)
    static_signals = state.get("static_signals", [])
    fast_mode = bool(state.get("fast_mode", False))

    if heuristic is not None:
        state["classification"] = heuristic
    elif fast_mode:
        state["classification"] = _fast_classification(parsed_report.body, static_signals)
    else:
        llm = ChatOllama(model=MODEL_NAME, temperature=0)
        structured_llm = llm.with_structured_output(ClassificationResult)
        prompt = (
            f"{prompt_template}\n\n"
            f"Runtime context:\n"
            f"- Concurrency hint from parser: {concurrency_hint}\n"
            f"- Project language: {state.get('language', 'unknown')}\n"
            f"- Static signals: {static_signals[:8]}\n\n"
            f"Bug report title: {parsed_report.title}\n"
            f"Bug report body:\n{parsed_report.body}\n\n"
            f"Extracted keywords: {parsed_report.error_keywords}"
        )
        result = structured_llm.invoke(prompt)
        state["classification"] = result.model_dump()

    state["status"] = "classified"
    append_jsonl_log(
        state["execution_log_path"],
        {
            "run_id": state.get("run_id"),
            "agent": "classifier",
            "status": state["status"],
            "duration_ms": round((perf_counter() - started_at) * 1000, 2),
            "input": state["bug_report"],
            "tool_calls": [
                {"tool": "parse_bug_report", "concurrency_hint": concurrency_hint},
                {"tool": "load_prompt", "prompt_file": PROMPT_FILE},
                *([{"tool": "heuristic_classification"}] if heuristic is not None else []),
                *([{"tool": "fast_mode_classification"}] if heuristic is None and fast_mode else []),
            ],
            "output": state["classification"],
        },
    )
    return state
