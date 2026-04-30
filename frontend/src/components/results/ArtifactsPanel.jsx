import { Panel } from "../common/Panel";
import { CodeBlock } from "../common/CodeBlock";

export function ArtifactsPanel({ result, reportUrl, patchUrl, rawJsonUrl }) {
  const reportName = result?.run_id ? `final_report_${result.run_id}.pdf` : undefined;
  const patchName = result?.run_id ? `patch_${result.run_id}.diff` : undefined;
  const jsonName = result?.run_id ? `run_result_${result.run_id}.json` : undefined;

  return (
    <Panel title="Artifacts">
      <p className="artifact-note">
        Download the detailed PDF report for submission or review, the generated patch diff, or the raw JSON output for
        debugging and evaluation.
      </p>
      <div className="artifact-links">
        <a
          className={`artifact-link ${reportUrl ? "" : "disabled"}`.trim()}
          href={reportUrl || "#"}
          target="_blank"
          rel="noreferrer"
          download={reportName}
        >
          Download PDF Report
        </a>
        <a
          className={`artifact-link ${patchUrl ? "" : "disabled"}`.trim()}
          href={patchUrl || "#"}
          target="_blank"
          rel="noreferrer"
          download={patchName}
        >
          Download Patch Diff
        </a>
        <a
          className={`artifact-link ${rawJsonUrl ? "" : "disabled"}`.trim()}
          href={rawJsonUrl || "#"}
          download={jsonName}
        >
          Download Raw JSON
        </a>
      </div>
      <CodeBlock value={result?.final_report_markdown || ""} />
    </Panel>
  );
}
