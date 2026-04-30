import { Panel } from "../common/Panel";
import { StatusPill } from "../common/StatusPill";

function getTone(status, running) {
  if (running) {
    return "running";
  }
  if (status === "tested") {
    return "success";
  }
  if (status === "rolled_back" || status === "failed") {
    return "error";
  }
  return "idle";
}

function formatConfidence(value) {
  if (typeof value !== "number") {
    return "-";
  }
  return `${Math.round(value * 100)}%`;
}

function formatElapsed(seconds) {
  const safe = Math.max(0, seconds);
  const minutes = Math.floor(safe / 60);
  const remainingSeconds = safe % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}`;
}

function formatExecutionMode(mode) {
  const labels = {
    full: "Full Workflow",
    classifier: "Classifier Only",
    root_cause: "Root Cause Only",
    fix_generator: "Fix Generator Only",
    tester: "Tester / Report Only",
  };
  return labels[mode] || "-";
}

export function ExecutionSummaryPanel({ result, running, elapsedSeconds, plannedExecutionMode }) {
  const status = running ? `running ${formatElapsed(elapsedSeconds)}` : result?.status || "idle";
  const executionMode = result?.execution_mode || plannedExecutionMode || "full";

  return (
    <Panel title="Execution Summary" action={<StatusPill tone={getTone(result?.status || "idle", running)}>{status}</StatusPill>}>
      <div className="summary-grid summary-grid-extended">
        <article className="summary-card">
          <span>Run ID</span>
          <strong>{result?.run_id || "-"}</strong>
        </article>
        <article className="summary-card">
          <span>Execution Mode</span>
          <strong>{formatExecutionMode(executionMode)}</strong>
        </article>
        <article className="summary-card">
          <span>Bug Type</span>
          <strong>{result?.classification?.bug_type || "-"}</strong>
        </article>
        <article className="summary-card">
          <span>Classifier Confidence</span>
          <strong>{formatConfidence(result?.classification?.confidence)}</strong>
        </article>
        <article className="summary-card">
          <span>Root Cause</span>
          <strong>{result?.root_cause ? `${result.root_cause.suspected_file} / ${result.root_cause.suspected_function}` : "-"}</strong>
        </article>
        <article className="summary-card">
          <span>Root Cause Confidence</span>
          <strong>{formatConfidence(result?.root_cause?.confidence)}</strong>
        </article>
        <article className="summary-card">
          <span>Patch Confidence</span>
          <strong>{formatConfidence(result?.patch?.confidence)}</strong>
        </article>
        <article className="summary-card">
          <span>Validation</span>
          <strong>{result?.test_results ? (result.test_results.passed ? "Passed" : result.status || "Failed") : running ? "In progress" : "-"}</strong>
        </article>
        <article className="summary-card">
          <span>Validation Confidence</span>
          <strong>{formatConfidence(result?.test_results?.confidence)}</strong>
        </article>
      </div>

      <div className="result-columns result-columns-stacked">
        <article className="result-card">
          <h3>Final Summary</h3>
          <p>
            {running
              ? `Workflow is still running locally through Ollama. Elapsed time: ${formatElapsed(elapsedSeconds)}. Current mode: ${formatExecutionMode(executionMode)}.`
              : result?.final_summary || "Run the workflow to see the end-to-end summary."}
          </p>
        </article>
        <article className="result-card">
          <h3>Validator Summary</h3>
          <p>{result?.test_results?.validator_summary || (running ? "Validation will begin after bug identification and patching complete." : "Validation insights will appear after a run.")}</p>
        </article>
      </div>

      <div className="result-columns">
        <article className="result-card">
          <h3>Evidence</h3>
          <ul className="evidence-list">
            {(result?.root_cause?.evidence || [running ? "Evidence will appear once the root-cause agent finishes." : "No evidence yet."]).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
        <article className="result-card">
          <h3>Static Signals</h3>
          <ul className="evidence-list">
            {(result?.static_signals?.slice(0, 6) || []).map((signal, index) => (
              <li key={`${signal.file}-${signal.tool}-${index}`}>
                <strong>{signal.tool}</strong>: {signal.summary}
              </li>
            ))}
            {!result?.static_signals?.length ? <li>{running ? "Static analysis results will appear once identification completes." : "No static signals yet."}</li> : null}
          </ul>
        </article>
      </div>
    </Panel>
  );
}
