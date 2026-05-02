"""
Observability and tracing for agent execution metrics.

Captures:
- Agent start and end times (duration)
- Tool call counts and outcomes
- Confidence scores at each decision point
- Routing decisions (why supervisor chose a path)
- Rollback events

This makes the system observable and defensible in the report.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    """Status of agent execution."""
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    HALTED = "halted"


@dataclass
class ToolMetrics:
    """Metrics for a single tool call."""
    name: str
    status: str  # "success", "failure", "skipped"
    duration_ms: float
    input_size: int = 0  # bytes
    output_size: int = 0
    error_message: str = ""


@dataclass
class AgentMetrics:
    """Metrics for a single agent execution."""
    agent_name: str
    status: AgentStatus
    started_at: float
    ended_at: float = 0.0
    duration_ms: float = 0.0
    
    input_confidence: float = 0.0  # Confidence of input state
    output_confidence: float = 0.0  # Confidence of output
    
    tool_calls: list[ToolMetrics] = field(default_factory=list)
    tool_success_count: int = 0
    tool_failure_count: int = 0
    
    llm_tokens_input: int = 0
    llm_tokens_output: int = 0
    
    routing_decision: str = ""  # Why supervisor chose this path
    hallucination_risk: str = ""  # "high", "medium", "low"
    state_validation_passed: bool = True
    
    def finalize(self) -> None:
        """Calculate derived metrics."""
        self.ended_at = time.time()
        self.duration_ms = (self.ended_at - self.started_at) * 1000
        
        for tool in self.tool_calls:
            if tool.status == "success":
                self.tool_success_count += 1
            elif tool.status == "failure":
                self.tool_failure_count += 1


@dataclass
class WorkflowMetrics:
    """Overall workflow metrics."""
    run_id: str
    bug_type: str = ""
    
    started_at: float = field(default_factory=time.time)
    ended_at: float = 0.0
    total_duration_ms: float = 0.0
    
    agent_metrics: dict[str, AgentMetrics] = field(default_factory=dict)
    
    supervisor_decisions: list[tuple[str, str]] = field(default_factory=list)  # (stage, decision)
    rollback_count: int = 0
    validation_passed: bool = False
    
    final_status: str = "unknown"
    
    def finalize(self) -> None:
        """Calculate total workflow metrics."""
        self.ended_at = time.time()
        self.total_duration_ms = (self.ended_at - self.started_at) * 1000
    
    def to_report_dict(self) -> dict[str, Any]:
        """Convert to dictionary suitable for final report."""
        return {
            "run_id": self.run_id,
            "bug_type": self.bug_type,
            "total_duration_ms": self.total_duration_ms,
            "validation_passed": self.validation_passed,
            "rollback_count": self.rollback_count,
            "final_status": self.final_status,
            "agents": {
                name: {
                    "status": metrics.status.value,
                    "duration_ms": metrics.duration_ms,
                    "input_confidence": f"{metrics.input_confidence:.2f}",
                    "output_confidence": f"{metrics.output_confidence:.2f}",
                    "tool_calls": len(metrics.tool_calls),
                    "tool_success": metrics.tool_success_count,
                    "tool_failures": metrics.tool_failure_count,
                    "hallucination_risk": metrics.hallucination_risk,
                    "routing_decision": metrics.routing_decision,
                }
                for name, metrics in self.agent_metrics.items()
            },
            "supervisor_routing": [
                {"stage": stage, "decision": decision}
                for stage, decision in self.supervisor_decisions
            ],
        }


class TraceRecorder:
    """Singleton-like recorder for workflow metrics."""
    
    _instance: TraceRecorder | None = None
    _metrics: WorkflowMetrics | None = None
    
    def __new__(cls) -> TraceRecorder:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self, run_id: str) -> None:
        """Initialize metrics for a new run."""
        self._metrics = WorkflowMetrics(run_id=run_id)
    
    def start_agent(self, agent_name: str) -> None:
        """Record agent start time."""
        if self._metrics is None:
            return
        metrics = AgentMetrics(
            agent_name=agent_name,
            status=AgentStatus.STARTED,
            started_at=time.time(),
        )
        self._metrics.agent_metrics[agent_name] = metrics
    
    def record_tool_call(self, agent_name: str, tool_metrics: ToolMetrics) -> None:
        """Record a tool call for an agent."""
        if self._metrics is None or agent_name not in self._metrics.agent_metrics:
            return
        self._metrics.agent_metrics[agent_name].tool_calls.append(tool_metrics)
    
    def set_agent_confidence(self, agent_name: str, input_conf: float, output_conf: float) -> None:
        """Set confidence scores for agent output."""
        if self._metrics is None or agent_name not in self._metrics.agent_metrics:
            return
        metrics = self._metrics.agent_metrics[agent_name]
        metrics.input_confidence = input_conf
        metrics.output_confidence = output_conf
    
    def set_agent_status(self, agent_name: str, status: AgentStatus, hallucination_risk: str = "low") -> None:
        """Mark agent as complete."""
        if self._metrics is None or agent_name not in self._metrics.agent_metrics:
            return
        metrics = self._metrics.agent_metrics[agent_name]
        metrics.status = status
        metrics.hallucination_risk = hallucination_risk
        metrics.finalize()
    
    def record_supervisor_decision(self, stage: str, decision: str) -> None:
        """Record supervisor routing decision."""
        if self._metrics is None:
            return
        self._metrics.supervisor_decisions.append((stage, decision))
    
    def set_bug_type(self, bug_type: str) -> None:
        """Set bug type from classification."""
        if self._metrics is None:
            return
        self._metrics.bug_type = bug_type
    
    def record_rollback(self) -> None:
        """Increment rollback counter."""
        if self._metrics is None:
            return
        self._metrics.rollback_count += 1
    
    def finalize_workflow(self, final_status: str, validation_passed: bool) -> WorkflowMetrics | None:
        """Finalize metrics and return completed metrics object."""
        if self._metrics is None:
            return None
        self._metrics.final_status = final_status
        self._metrics.validation_passed = validation_passed
        self._metrics.finalize()
        result = self._metrics
        self._metrics = None
        return result
    
    def get_metrics(self) -> WorkflowMetrics | None:
        """Get current metrics (read-only)."""
        return self._metrics


def get_trace_recorder() -> TraceRecorder:
    """Get or create the global trace recorder."""
    return TraceRecorder()
