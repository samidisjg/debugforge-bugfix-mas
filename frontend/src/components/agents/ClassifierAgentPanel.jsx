import PropTypes from "prop-types";
import { AgentCard } from "./AgentCard";

export function ClassifierAgentPanel({ result }) {
  const payload = result?.classification
    ? {
        classification: result.classification,
        staticSignalsUsed: result?.static_signals?.slice(0, 4) || [],
      }
    : null;

  return (
    <AgentCard
      title="Agent 1 - Classifier"
      subtitle="Classifies the incoming issue from the bug report, runtime hints, and early static signals."
      value={payload ? JSON.stringify(payload, null, 2) : ""}
      role="classifier"
    />
  );
}

ClassifierAgentPanel.propTypes = {
  result: PropTypes.object,
};

ClassifierAgentPanel.defaultProps = {
  result: null,
};
