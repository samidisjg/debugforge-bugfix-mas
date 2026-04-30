import PropTypes from "prop-types";
import { Panel } from "../common/Panel";
import { CodeBlock } from "../common/CodeBlock";

function roleLabel(role) {
  if (role === "classifier") return "CL";
  if (role === "root-cause") return "RC";
  if (role === "fix-generator") return "FX";
  if (role === "tester") return "TS";
  return "AG";
}

export function AgentCard({ title, subtitle, value, role }) {
  const badge = (
    <div className={`agent-mini-robot ${role}`.trim()} aria-hidden="true">
      <span className="mini-antenna" />
      <span className="mini-head">
        <span className="mini-eye" />
        <span className="mini-eye" />
      </span>
      <span className="mini-body">{roleLabel(role)}</span>
    </div>
  );

  return (
    <Panel title={title} className="agent-card" action={badge}>
      <p className="agent-subtitle">{subtitle}</p>
      <CodeBlock value={value} />
    </Panel>
  );
}

AgentCard.propTypes = {
  title: PropTypes.string.isRequired,
  subtitle: PropTypes.string.isRequired,
  value: PropTypes.string,
  role: PropTypes.oneOf(["classifier", "root-cause", "fix-generator", "tester"]),
};

AgentCard.defaultProps = {
  value: "",
  role: "classifier",
};
