import PropTypes from "prop-types";
import { AgentCard } from "./AgentCard";

export function RootCauseAgentPanel({ result }) {
  const payload = result?.root_cause
    ? {
        rootCause: result.root_cause,
        topSearchMatches: result?.search_matches?.slice(0, 5) || [],
        llmContext: result?.llm_context || {},
      }
    : null;

  return (
    <AgentCard
      title="Agent 2 - Root Cause"
      subtitle="Ranks evidence, uses localized code context, and selects the most likely fault site."
      value={payload ? JSON.stringify(payload, null, 2) : ""}
      role="root-cause"
    />
  );
}

RootCauseAgentPanel.propTypes = {
  result: PropTypes.object,
};

RootCauseAgentPanel.defaultProps = {
  result: null,
};
