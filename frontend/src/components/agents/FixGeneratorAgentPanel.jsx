import PropTypes from "prop-types";
import { AgentCard } from "./AgentCard";

export function FixGeneratorAgentPanel({ result }) {
  return (
    <AgentCard
      title="Agent 3 - Fix Generator"
      subtitle="Builds the patch, backup file, and diff artifact for the suspected bug."
      value={result?.patch ? JSON.stringify(result.patch, null, 2) : ""}
      role="fix-generator"
    />
  );
}

FixGeneratorAgentPanel.propTypes = {
  result: PropTypes.shape({
    patch: PropTypes.any,
  }),
};

FixGeneratorAgentPanel.defaultProps = {
  result: null,
};
