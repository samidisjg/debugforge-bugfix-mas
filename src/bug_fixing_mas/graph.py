from __future__ import annotations

from langgraph.graph import END, StateGraph

from bug_fixing_mas.classifier_agent.agent_classifier import classifier_agent
from bug_fixing_mas.root_cause_agent.agent_root_cause import root_cause_agent
from bug_fixing_mas.fix_generator_agent.agent_fix_generator import fix_generator_agent
from bug_fixing_mas.tester_agent.agent_tester import tester_agent
from bug_fixing_mas.shared.logging_utils import append_jsonl_log
from bug_fixing_mas.shared.state import BugFixState
from bug_fixing_mas.supervisor import (
    explain_routing_decision,
    route_after_classification,
    route_after_fix_generator,
    route_after_root_cause,
)


def _record_supervisor_decision(state: BugFixState, stage: str, decision: str) -> None:
    observability = state.setdefault("observability", {})
    routing = observability.setdefault("supervisor_routing", [])
    explanation = explain_routing_decision(state, decision)
    routing.append({"stage": stage, "decision": decision, "explanation": explanation})

    if state.get("execution_log_path"):
        append_jsonl_log(
            state["execution_log_path"],
            {
                "run_id": state.get("run_id"),
                "agent": "supervisor",
                "status": stage,
                "tool_calls": [{"tool": "route_decision", "stage": stage, "decision": decision}],
                "output": {"stage": stage, "decision": decision, "explanation": explanation},
            },
        )


def _route_after_classification(state: BugFixState) -> str:
    decision = route_after_classification(state)
    _record_supervisor_decision(state, "after_classification", decision)
    return decision


def _route_after_root_cause(state: BugFixState) -> str:
    decision = route_after_root_cause(state)
    _record_supervisor_decision(state, "after_root_cause", decision)
    return decision


def _route_after_fix_generator(state: BugFixState) -> str:
    decision = route_after_fix_generator(state)
    _record_supervisor_decision(state, "after_fix_generator", decision)
    return decision


def build_graph():
    """Build an adaptive multi-agent graph with supervisor-driven routing."""
    graph = StateGraph(BugFixState)

    graph.add_node("classifier", classifier_agent)
    graph.add_node("root_cause", root_cause_agent)
    graph.add_node("fix_generator", fix_generator_agent)
    graph.add_node("tester", tester_agent)

    graph.set_entry_point("classifier")

    graph.add_conditional_edges(
        "classifier",
        _route_after_classification,
        {
            "proceed_to_root_cause": "root_cause",
            "attempt_heuristic_fix": "root_cause",
            "halt_low_confidence": END,
        },
    )

    graph.add_conditional_edges(
        "root_cause",
        _route_after_root_cause,
        {
            "proceed_to_fix_generator": "fix_generator",
            "escalate_root_cause": "fix_generator",
            "retry_with_llm_context": "fix_generator",
            "halt_insufficient_evidence": END,
        },
    )

    graph.add_conditional_edges(
        "fix_generator",
        _route_after_fix_generator,
        {
            "proceed_with_caution_to_tester": "tester",
            "proceed_to_tester": "tester",
            "halt_uncertain_patch": END,
        },
    )

    graph.add_edge("tester", END)
    return graph.compile()
