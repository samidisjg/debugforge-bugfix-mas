import PropTypes from "prop-types";
import { AgentCard } from "./AgentCard";

export function TesterAgentPanel({ result }) {
  const payload = result?.test_results
    ? {
        validation: result.test_results,
        finalSummary: result?.final_summary || "",
      }
    : null;

  return (
    <AgentCard
      title="Agent 4 - Tester / Report"
      subtitle="Runs layered validation, compares before/after behavior, and writes the final downloadable report."
      value={payload ? JSON.stringify(payload, null, 2) : ""}
      role="tester"
    />
  );
}

TesterAgentPanel.propTypes = {
  result: PropTypes.object,
};

TesterAgentPanel.defaultProps = {
  result: null,
};
