import { Panel } from "../common/Panel";
import { StatusPill } from "../common/StatusPill";

const EXECUTION_MODE_LABELS = {
  full: "Run Full Workflow",
  classifier: "Run Classifier Agent",
  root_cause: "Run Root Cause Agent",
  fix_generator: "Run Fix Generator Agent",
  tester: "Run Tester / Report Agent",
};

export function RunConfigurationPanel({
  apiReady,
  form,
  demoProjects,
  uploadedFiles,
  running,
  onModeChange,
  onFieldChange,
  onDemoChange,
  onFileChange,
  onRun,
  onReset,
}) {
  const runLabel = EXECUTION_MODE_LABELS[form.executionMode] || "Run MAS";

  return (
    <Panel
      title="Run Configuration"
      action={<StatusPill tone={apiReady ? "success" : "error"}>{apiReady ? "API Ready" : "API Offline"}</StatusPill>}
    >
      <label className="field">
        <span>Input Mode</span>
        <select value={form.mode} onChange={(event) => onModeChange(event.target.value)}>
          <option value="custom">Custom Upload</option>
          <option value="demo">Demo Project</option>
        </select>
      </label>

      <label className="field">
        <span>Execution Mode</span>
        <select value={form.executionMode} onChange={(event) => onFieldChange("executionMode", event.target.value)}>
          <option value="full">Full Workflow</option>
          <option value="classifier">Classifier Only</option>
          <option value="root_cause">Root Cause Only</option>
          <option value="fix_generator">Fix Generator Only</option>
          <option value="tester">Tester / Report Only</option>
        </select>
        <small>Single-agent modes automatically prepare prerequisites first, while Full Workflow preserves the main LangGraph orchestration.</small>
      </label>

      {form.mode === "demo" ? (
        <>
          <label className="field">
            <span>Demo Project</span>
            <select value={form.demoId} onChange={(event) => onDemoChange(event.target.value)}>
              {demoProjects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.label}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <span>Project Path</span>
            <input
              type="text"
              value={form.projectPath}
              onChange={(event) => onFieldChange("projectPath", event.target.value)}
              placeholder="Absolute or workspace path"
            />
          </label>
        </>
      ) : (
        <label className="field">
          <span>Upload Files</span>
          <input type="file" multiple onChange={(event) => onFileChange(event.target.files)} />
          <small>Upload one or more source or test files. Short prompts like `fix bug` are supported.</small>
        </label>
      )}

      <label className="field">
        <span>Language</span>
        <select value={form.language} onChange={(event) => onFieldChange("language", event.target.value)}>
          <option value="python">Python</option>
          <option value="java">Java</option>
          <option value="javascript">JavaScript</option>
          <option value="go">Go</option>
        </select>
      </label>

      <div className="field toggle-field">
        <div className="toggle-row">
          <div className="toggle-copy">
            <span>Fast Mode</span>
            <small>Use the faster heuristic path for simple uploaded files.</small>
          </div>
          <button
            type="button"
            className={`toggle-switch ${form.fastMode ? "is-on" : "is-off"}`}
            aria-pressed={Boolean(form.fastMode)}
            onClick={() => onFieldChange("fastMode", !form.fastMode)}
          >
            <span className="toggle-thumb" />
          </button>
        </div>
      </div>

      <label className="field">
        <span>Bug Report</span>
        <textarea
          rows="7"
          value={form.bugReport}
          onChange={(event) => onFieldChange("bugReport", event.target.value)}
          placeholder="Describe the bug or simply type: fix bug"
        />
      </label>

      <p className="form-note">This page now keeps your latest form inputs, uploaded file payloads, run result, and timeline after refresh. Use Clear Data when you want a fresh start.</p>

      {uploadedFiles.length ? (
        <div className="uploaded-files">
          {uploadedFiles.map((file) => (
            <span key={file.filename} className="file-chip">
              {file.filename}
            </span>
          ))}
        </div>
      ) : null}

      <div className="button-row">
        <button type="button" className="primary-button" disabled={running} onClick={onRun}>
          {running ? "Running..." : runLabel}
        </button>
      </div>
    </Panel>
  );
}
