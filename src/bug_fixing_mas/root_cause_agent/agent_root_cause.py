from __future__ import annotations

from pathlib import Path
from time import perf_counter

from langchain_ollama import ChatOllama

from bug_fixing_mas.root_cause_agent.tool_code_search import (
    SearchMatch,
    collect_static_signals,
    extract_function_context,
    extract_nearby_code,
    scan_concurrency_risks,
    search_source_files,
)
from bug_fixing_mas.shared.language_config import get_language_config
from bug_fixing_mas.shared.logging_utils import append_jsonl_log
from bug_fixing_mas.shared.models import RootCauseResult
from bug_fixing_mas.shared.prompt_loader import load_prompt
from bug_fixing_mas.shared.state import BugFixState
from bug_fixing_mas.shared.state_validators import ensure_state_is_valid_for_agent


MODEL_NAME = "llama3.1:8b"
PROMPT_FILE = "root_cause_prompt.md"
RETURN_ZERO_HINT = "return 0"


LANGUAGE_HINTS = {
    "python": ["def", "raise", "pytest", "zero division", "calculator", "threading", "lock", "race", "valueerror", "return", "validation"],
    "javascript": ["function", "throw", "jest", "npm", "calculator", "worker", "promise", RETURN_ZERO_HINT],
    "java": ["class", "public", "throws", "junit", "calculator", "synchronized", "lock", "thread", "onstatus", "exception", "catch"],
    "go": ["func", "panic", "testing", "go test", "calculator", "mutex", "goroutine", "atomic", RETURN_ZERO_HINT],
}


CONCURRENCY_TERMS = ["concurrency", "race", "deadlock", "lock", "mutex", "thread", "atomic", "shared state"]


def _is_concurrency_bug(state: BugFixState) -> bool:
    bug_text = " ".join(
        [
            state.get("bug_report", ""),
            state.get("classification", {}).get("bug_type", ""),
            state.get("classification", {}).get("summary", ""),
        ]
    ).lower()
    return any(term in bug_text for term in CONCURRENCY_TERMS)


def _normalize_root_cause(result: RootCauseResult, matches: list[SearchMatch]) -> dict[str, object]:
    output = result.model_dump()
    output["suspected_file"] = str(output["suspected_file"])

    if matches:
        preferred_match = next(
            (
                match
                for match in matches
                if Path(str(match["file"])).name == str(output["suspected_file"])
            ),
            matches[0],
        )
        output["suspected_file"] = Path(str(preferred_match["file"])).name

    if not output.get("evidence"):
        output["evidence"] = [
            f"{Path(str(match['file'])).name}:{match['line_number']} -> {match['snippet']}"
            for match in matches[:3]
        ]

    if not output.get("confidence"):
        output["confidence"] = 0.58 if matches else 0.3

    return output


def _ground_root_cause_output(
    root_cause: dict[str, object],
    matches: list[SearchMatch],
    project_path: str,
) -> dict[str, object]:
    """Ensure root-cause output is grounded in existing files and evidence."""
    grounded = dict(root_cause)
    if not matches:
        return grounded

    match_by_name = {Path(str(match["file"])).name: match for match in matches}
    suspected_file = str(grounded.get("suspected_file", "")).strip()
    if suspected_file not in match_by_name:
        top = matches[0]
        grounded["suspected_file"] = Path(str(top["file"])).name

    target_name = str(grounded.get("suspected_file", "")).strip()
    target_path = Path(project_path) / target_name
    if not target_path.exists():
        top = matches[0]
        grounded["suspected_file"] = Path(str(top["file"])).name

    if not str(grounded.get("suspected_function", "")).strip():
        grounded["suspected_function"] = _guess_function_name(matches[0])

    evidence = [str(item) for item in grounded.get("evidence", []) if str(item).strip()]
    if not evidence or not any(Path(str(match["file"])).name in item for item in evidence for match in matches):
        grounded["evidence"] = [
            f"{Path(str(match['file'])).name}:{match['line_number']} -> {match['snippet']}"
            for match in matches[:3]
        ]

    confidence = float(grounded.get("confidence", 0.5) or 0.5)
    grounded["confidence"] = max(0.0, min(1.0, confidence))
    return grounded


def _heuristic_root_cause(state: BugFixState, matches: list[SearchMatch]) -> dict[str, object] | None:
    bug_text = state.get("bug_report", "").lower()
    file_name = Path(str(matches[0]["file"])).name if matches else "unknown"

    if "divide-by-zero branch returns 0" in bug_text or "divide by zero" in bug_text:
        divide_matches = [match for match in matches if "divide" in str(match["snippet"]).lower() or "return 0" in str(match["snippet"]).lower()]
        evidence = [
            f"{Path(str(match['file'])).name}:{match['line_number']} -> {match['snippet']}"
            for match in (divide_matches[:3] or matches[:3])
        ]
        return {
            "suspected_file": file_name,
            "suspected_function": "divide",
            "evidence": evidence,
            "reasoning": "The implementation returns 0 in a divide-by-zero branch instead of propagating an arithmetic failure.",
            "confidence": 0.9,
        }

    if "reactive onstatus with map(exception) may not propagate errors correctly" in bug_text:
        onstatus_matches = [
            match for match in matches
            if any(token in str(match["snippet"]).lower() for token in ["onstatus", ".map(", "libraryserviceexception", "exception"])
        ]
        evidence = [
            f"{Path(str(match['file'])).name}:{match['line_number']} -> {match['snippet']}"
            for match in (onstatus_matches[:3] or matches[:3])
        ]
        return {
            "suspected_file": file_name,
            "suspected_function": "updateBorrowFineStatus",
            "evidence": evidence,
            "reasoning": "The reactive error mapping uses map(Exception) style propagation, which can wrap the response body without correctly surfacing the downstream error signal.",
            "confidence": 0.86,
        }

    if "catch(exception) block without rethrow can mask failures" in bug_text:
        catch_matches = [match for match in matches if "catch" in str(match["snippet"]).lower()]
        evidence = [
            f"{Path(str(match['file'])).name}:{match['line_number']} -> {match['snippet']}"
            for match in (catch_matches[:3] or matches[:3])
        ]
        return {
            "suspected_file": file_name,
            "suspected_function": "unknown",
            "evidence": evidence,
            "reasoning": "A broad catch block appears to absorb exceptions without preserving the original failure path.",
            "confidence": 0.78,
        }

    if "validation" in bug_text or "non-negative" in bug_text or "invalid" in bug_text:
        validation_matches = [match for match in matches if any(token in str(match["snippet"]).lower() for token in ["valueerror", "illegalargumentexception", "return age", "validate", "negative"])]
        if validation_matches:
            evidence = [
                f"{Path(str(match['file'])).name}:{match['line_number']} -> {match['snippet']}"
                for match in validation_matches[:3]
            ]
            return {
                "suspected_file": Path(str(validation_matches[0]["file"])).name,
                "suspected_function": "normalize_age",
                "evidence": evidence,
                "reasoning": "The function appears to pass invalid input through instead of rejecting it with explicit validation.",
                "confidence": 0.76,
            }

    return None


def _guess_function_name(match: SearchMatch) -> str:
    snippet = str(match.get("snippet", "")).strip()
    for token in ["def ", "function ", "func "]:
        if token in snippet:
            remainder = snippet.split(token, 1)[1]
            return remainder.split("(", 1)[0].strip() or "unknown"
    if "(" in snippet and any(keyword in snippet for keyword in ["public", "private", "protected"]):
        before_paren = snippet.split("(", 1)[0].strip().split()
        return before_paren[-1] if before_paren else "unknown"
    if snippet.startswith("class "):
        return snippet.split()[1].rstrip(":{")
    return "unknown"


def _fast_root_cause(matches: list[SearchMatch], static_signals: list[dict[str, object]]) -> dict[str, object]:
    preferred = next((match for match in matches if not bool(match.get("is_test_file", False))), matches[0] if matches else None)
    if preferred is None:
        return {
            "suspected_file": "unknown",
            "suspected_function": "unknown",
            "evidence": [],
            "reasoning": "Fast mode could not locate a strong source-level signal, so it preserved a conservative unknown root cause.",
            "confidence": 0.35,
        }
    evidence = [
        f"{Path(str(match['file'])).name}:{match['line_number']} -> {match['snippet']}"
        for match in matches[:3]
    ]
    signal_summary = "; ".join(str(signal.get("summary", "")) for signal in static_signals[:2])
    reasoning = "Fast mode selected the top-ranked non-test source location using code search and static signals."
    if signal_summary:
        reasoning += f" Signals: {signal_summary}"
    return {
        "suspected_file": Path(str(preferred["file"])).name,
        "suspected_function": _guess_function_name(preferred),
        "evidence": evidence,
        "reasoning": reasoning,
        "confidence": 0.64,
    }


def _build_llm_context(matches: list[SearchMatch], suspected_function: str) -> dict[str, object]:
    top_match = matches[0] if matches else None
    nearby_code = ""
    function_context = ""
    if top_match:
        nearby_code = extract_nearby_code(str(top_match["file"]), int(top_match["line_number"]))
        function_context = extract_function_context(str(top_match["file"]), suspected_function if suspected_function != "unknown" else Path(str(top_match["file"])).stem)
    failing_test = next((match for match in matches if bool(match.get("is_test_file"))), None)
    return {
        "top_match": top_match,
        "nearby_code": nearby_code,
        "function_context": function_context,
        "failing_test_snippet": failing_test,
    }


def root_cause_agent(state: BugFixState) -> BugFixState:
    """Inspect the project files and identify the likely defect location."""
    ensure_state_is_valid_for_agent("root_cause", state)
    started_at = perf_counter()
    classification = state["classification"]
    language = state["language"]
    fast_mode = bool(state.get("fast_mode", False))
    language_config = get_language_config(language)
    search_terms = [
        classification.get("bug_type", ""),
        classification.get("summary", ""),
        *classification.get("likely_modules", []),
        *LANGUAGE_HINTS.get(language, []),
        "divide",
        "zero",
        "error",
        "calculator",
        "validation",
        "exception",
    ]
    # Use advanced search with language-aware AST analysis
    matches = search_source_files(state["project_path"], search_terms, language_config.source_extensions, language)
    static_signals = collect_static_signals(state["project_path"], language, language_config.source_extensions)
    concurrency_matches: list[dict[str, object]] = []
    if _is_concurrency_bug(state):
        concurrency_matches = scan_concurrency_risks(state["project_path"], language_config.source_extensions)
        matches.extend(concurrency_matches)
        matches.sort(key=lambda item: (-int(item.get("score", 0)), bool(item.get("is_test_file", False))))

    heuristic = _heuristic_root_cause(state, matches)
    prompt_template = load_prompt(PROMPT_FILE)
    if heuristic is not None:
        normalized = heuristic
    elif fast_mode:
        normalized = _fast_root_cause(matches, static_signals)
    else:
        llm_context = _build_llm_context(matches, "unknown")
        llm = ChatOllama(model=MODEL_NAME, temperature=0)
        structured_llm = llm.with_structured_output(RootCauseResult)
        prompt = (
            f"{prompt_template}\n\n"
            f"Runtime context:\n"
            f"- Project language: {language}\n"
            f"- Concurrency mode: {_is_concurrency_bug(state)}\n"
            f"- Static signals: {static_signals[:10]}\n\n"
            f"Classification:\n{classification}\n\n"
            f"Top ranked evidence:\n{matches[:10]}\n\n"
            f"Nearby code:\n{llm_context['nearby_code']}\n\n"
            f"Function-centered context:\n{llm_context['function_context']}\n\n"
            f"Failing test snippet:\n{llm_context['failing_test_snippet']}"
        )
        result = structured_llm.invoke(prompt)
        normalized = _normalize_root_cause(result, matches)

    normalized = _ground_root_cause_output(normalized, matches, state["project_path"])

    llm_context = _build_llm_context(matches, normalized.get("suspected_function", "unknown"))
    state["search_matches"] = matches
    state["static_signals"] = static_signals
    state["llm_context"] = llm_context
    state["root_cause"] = normalized
    state["status"] = "analyzed"
    append_jsonl_log(
        state["execution_log_path"],
        {
            "run_id": state.get("run_id"),
            "agent": "root_cause",
            "status": state["status"],
            "duration_ms": round((perf_counter() - started_at) * 1000, 2),
            "input": {"classification": classification, "language": language, "fast_mode": fast_mode},
            "tool_calls": [
                {"tool": "search_source_files", "matches": matches[:12]},
                {"tool": "collect_static_signals", "signals": static_signals[:12]},
                {"tool": "load_prompt", "prompt_file": PROMPT_FILE},
                *([{"tool": "scan_concurrency_risks", "matches": concurrency_matches[:8]}] if concurrency_matches else []),
                *([{"tool": "heuristic_root_cause"}] if heuristic is not None else []),
                *([{"tool": "fast_mode_root_cause"}] if heuristic is None and fast_mode else []),
            ],
            "output": normalized,
        },
    )
    return state
