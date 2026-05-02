"""
Supervisor agent: Route the workflow based on bug type, confidence, and validation state.

This is the "real agent system" improvement. Instead of a fixed linear pipeline,
the supervisor makes intelligent routing decisions that adapt to:
- Bug type (concurrency vs arithmetic vs validation vs logic)
- Agent confidence scores
- Validation outcomes
- Rollback triggers

This allows for sophisticated multi-agent orchestration with adaptive branching.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from bug_fixing_mas.shared.state import BugFixState


class RouteDecision(str, Enum):
    """Supervisor routing decisions."""
    PROCEED_STANDARD = "proceed_standard_path"  # Normal path
    ESCALATE_ROOT_CAUSE = "escalate_root_cause"  # Need deeper analysis
    SKIP_TO_TESTER = "skip_to_tester"  # High-confidence shortcut
    ATTEMPT_HEURISTIC_FIX = "attempt_heuristic_fix"  # Use pattern matching first
    RETRY_WITH_LLMCONTEXT = "retry_with_llm_context"  # Rerun with better context
    HALT_LOW_CONFIDENCE = "halt_low_confidence"  # Stop - too uncertain
    HALT_VALIDATION_FAILURE = "halt_validation_failure"  # Stop - tests failed
    ESCALATE_TO_MANUAL = "escalate_to_manual"  # Recommend manual intervention
    

def _get_bug_category(state: BugFixState) -> str:
    """Extract bug category from classification."""
    classification = state.get("classification", {})
    bug_type = str(classification.get("bug_type", "Unknown")).lower()
    return bug_type


def _get_average_confidence(state: BugFixState) -> float:
    """Calculate average confidence across agents."""
    scores = []
    
    if "classification" in state:
        scores.append(float(state["classification"].get("confidence", 0.0)))
    if "root_cause" in state:
        scores.append(float(state["root_cause"].get("confidence", 0.0)))
    if "patch" in state:
        scores.append(float(state["patch"].get("confidence", 0.0)))
    
    return sum(scores) / len(scores) if scores else 0.0


def route_after_classification(state: BugFixState) -> Literal[
    "proceed_to_root_cause",
    "halt_low_confidence",
    "attempt_heuristic_fix",
]:
    """
    Route after classifier finishes.
    
    Decision logic:
    - If confidence >= 0.75: proceed normally
    - If confidence 0.5-0.75: proceed but mark for escalation
    - If confidence < 0.5: halt
    """
    classification = state.get("classification", {})
    confidence = float(classification.get("confidence", 0.0))
    bug_type = _get_bug_category(state)
    
    # Very low confidence: halt
    if confidence < 0.5:
        return "halt_low_confidence"
    
    # For concurrency bugs, try heuristic patterns first (faster)
    if bug_type == "concurrency bug" and confidence >= 0.65:
        return "attempt_heuristic_fix"
    
    # Normal path: proceed to root cause analysis
    return "proceed_to_root_cause"


def route_after_root_cause(state: BugFixState) -> Literal[
    "proceed_to_fix_generator",
    "halt_insufficient_evidence",
    "retry_with_llm_context",
    "escalate_root_cause",
]:
    """
    Route after root_cause agent finishes.
    
    Decision logic:
    - If confidence >= 0.65 and evidence exists: proceed
    - If confidence 0.4-0.65: proceed but escalate for review
    - If no evidence or confidence < 0.4: retry with better context
    - If still failed: halt
    """
    root_cause = state.get("root_cause", {})
    confidence = float(root_cause.get("confidence", 0.0))
    evidence = root_cause.get("evidence", [])
    
    # No evidence at all: halt
    if not evidence:
        return "halt_insufficient_evidence"
    
    # Strong confidence and evidence: proceed
    if confidence >= 0.65 and len(evidence) >= 2:
        return "proceed_to_fix_generator"
    
    # Medium confidence: escalate for review
    if confidence >= 0.50 and len(evidence) >= 1:
        return "escalate_root_cause"
    
    # Low confidence but some evidence: retry with LLM context
    if confidence >= 0.35 and len(evidence) >= 1:
        return "retry_with_llm_context"
    
    # Too uncertain: halt
    return "halt_insufficient_evidence"


def route_after_fix_generator(state: BugFixState) -> Literal[
    "proceed_to_tester",
    "proceed_with_caution_to_tester",
    "halt_uncertain_patch",
]:
    """
    Route after fix_generator finishes.
    
    Decision logic:
    - If confidence >= 0.75: proceed normally
    - If confidence 0.3-0.75: proceed with caution (mark for review)
    - If confidence < 0.3: halt (too risky to apply patch)
    """
    patch = state.get("patch", {})
    confidence = float(patch.get("confidence", 0.0))
    
    # Too uncertain to apply: halt
    if confidence < 0.3:
        return "halt_uncertain_patch"
    
    # Medium confidence: proceed with caution
    if confidence < 0.7:
        return "proceed_with_caution_to_tester"
    
    # Good confidence: proceed normally
    return "proceed_to_tester"


def route_after_validation(state: BugFixState) -> Literal[
    "accept_fix",
    "rollback_and_halt",
    "retry_fix_generation",
]:
    """
    Route after tester finishes (validation gate).
    
    Decision logic:
    - If tests pass: accept fix
    - If tests failed but patch confidence was low: rollback and halt
    - If tests failed but patch confidence was high: retry fix generation
    """
    test_results = state.get("test_results", {})
    patch = state.get("patch", {})
    
    # Tests passed: accept
    if test_results.get("passed", False):
        return "accept_fix"
    
    # Tests failed
    patch_confidence = float(patch.get("confidence", 0.0))
    
    # If patch confidence was already low, don't retry (rollback)
    if patch_confidence < 0.5:
        return "rollback_and_halt"
    
    # Patch had high confidence but tests failed: try another approach
    return "retry_fix_generation"


def supervisor_decision(state: BugFixState, current_stage: str) -> str:
    """
    Main supervisor routing function.
    
    Current stages:
    - "initialized": Just received bug report
    - "classified": After classifier
    - "analyzed": After root_cause
    - "patched": After fix_generator
    - "validated": After tester
    """
    
    if current_stage == "classified":
        return route_after_classification(state)
    elif current_stage == "analyzed":
        return route_after_root_cause(state)
    elif current_stage == "patched":
        return route_after_fix_generator(state)
    elif current_stage == "validated":
        return route_after_validation(state)
    
    # Unknown stage
    return "proceed_standard_path"


def explain_routing_decision(state: BugFixState, decision: str) -> str:
    """
    Human-readable explanation of why the supervisor made this routing decision.
    
    Used for report generation and debugging.
    """
    classification = state.get("classification", {})
    root_cause = state.get("root_cause", {})
    patch = state.get("patch", {})
    
    explanations = {
        "proceed_to_root_cause": f"Classifier confidence is adequate ({classification.get('confidence', 0.0):.2f}). Proceeding to root cause analysis.",
        "halt_low_confidence": f"Classifier confidence too low ({classification.get('confidence', 0.0):.2f} < 0.5). Halting to prevent propagation of low-signal classification.",
        "attempt_heuristic_fix": f"Concurrency bug detected with good confidence ({classification.get('confidence', 0.0):.2f}). Attempting heuristic pattern-based fix first (faster).",
        "proceed_to_fix_generator": f"Root cause analysis confident ({root_cause.get('confidence', 0.0):.2f}) with {len(root_cause.get('evidence', []))} evidence lines. Proceeding to patch generation.",
        "halt_insufficient_evidence": f"Root cause has no supporting evidence. Halting to prevent speculative patching.",
        "escalate_root_cause": f"Root cause confidence moderate ({root_cause.get('confidence', 0.0):.2f}). Escalating for manual review before patching.",
        "retry_with_llm_context": f"Root cause confidence low ({root_cause.get('confidence', 0.0):.2f}) but some evidence exists. Retrying with enhanced LLM context.",
        "proceed_with_caution_to_tester": f"Patch confidence moderate ({patch.get('confidence', 0.0):.2f}). Applying patch but flagging for rigorous validation.",
        "proceed_to_tester": f"Patch confidence strong ({patch.get('confidence', 0.0):.2f}). Proceeding with standard validation.",
        "halt_uncertain_patch": f"Patch confidence critically low ({patch.get('confidence', 0.0):.2f} < 0.3). Too risky to apply without redesign.",
        "accept_fix": "Validation tests passed. Accepting fix as solution.",
        "rollback_and_halt": "Tests failed and patch confidence was already low. Rolling back to original and halting.",
        "retry_fix_generation": "Tests failed but patch confidence was high. Retrying fix generation with alternative approach.",
    }
    
    return explanations.get(decision, f"Routing decision: {decision}")
