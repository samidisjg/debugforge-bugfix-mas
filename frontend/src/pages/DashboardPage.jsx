import { useEffect, useMemo, useState } from "react";
import { ClassifierAgentPanel } from "../components/agents/ClassifierAgentPanel";
import { FixGeneratorAgentPanel } from "../components/agents/FixGeneratorAgentPanel";
import { RootCauseAgentPanel } from "../components/agents/RootCauseAgentPanel";
import { TesterAgentPanel } from "../components/agents/TesterAgentPanel";
import { RunConfigurationPanel } from "../components/forms/RunConfigurationPanel";
import { AppHeader } from "../components/layout/AppHeader";
import { ArtifactsPanel } from "../components/results/ArtifactsPanel";
import { ExecutionSummaryPanel } from "../components/results/ExecutionSummaryPanel";
import { RawResultPanel } from "../components/results/RawResultPanel";
import { TimelinePanel } from "../components/results/TimelinePanel";
import { api, buildPatchUrl, buildReportPdfUrl } from "../services/api";
import { filesToPayload, inferLanguageFromFilename } from "../utils/files";

const STORAGE_KEY = "bug-fixing-mas-dashboard-state";

function createInitialForm() {
  return {
    mode: "custom",
    executionMode: "full",
    demoId: "",
    language: "python",
    projectPath: "",
    bugReport: "fix bug",
    fastMode: true,
  };
}

function loadPersistedState() {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function DashboardPage() {
  const persisted = loadPersistedState();
  const [apiReady, setApiReady] = useState(false);
  const [demoProjects, setDemoProjects] = useState([]);
  const [form, setForm] = useState(persisted?.form ?? createInitialForm());
  const [uploadedFiles, setUploadedFiles] = useState(persisted?.uploadedFiles ?? []);
  const [running, setRunning] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [result, setResult] = useState(persisted?.result ?? null);
  const [timeline, setTimeline] = useState(persisted?.timeline ?? []);

  useEffect(() => {
    api.health().then(() => setApiReady(true)).catch(() => setApiReady(false));
    api
      .demoProjects()
      .then((projects) => {
        setDemoProjects(projects);
        if (projects.length && !persisted?.form?.demoId) {
          setForm((current) => ({ ...current, demoId: projects[0].id }));
        }
      })
      .catch(() => setDemoProjects([]));
  }, []);

  useEffect(() => {
    if (!running) {
      return undefined;
    }
    const intervalId = window.setInterval(() => {
      setElapsedSeconds((current) => current + 1);
    }, 1000);
    return () => window.clearInterval(intervalId);
  }, [running]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const payload = {
      form,
      uploadedFiles,
      result,
      timeline,
    };
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  }, [form, uploadedFiles, result, timeline]);

  const reportUrl = useMemo(() => (result?.run_id ? buildReportPdfUrl(result.run_id) : ""), [result]);
  const patchUrl = useMemo(() => (result?.run_id ? buildPatchUrl(result.run_id) : ""), [result]);
  const rawJsonUrl = useMemo(() => {
    if (!result) {
      return "";
    }
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    return URL.createObjectURL(blob);
  }, [result]);

  useEffect(() => {
    return () => {
      if (rawJsonUrl) {
        URL.revokeObjectURL(rawJsonUrl);
      }
    };
  }, [rawJsonUrl]);

  function onFieldChange(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function onModeChange(mode) {
    setForm((current) => ({ ...current, mode }));
  }

  function onDemoChange(demoId) {
    const selected = demoProjects.find((project) => project.id === demoId);
    setForm((current) => ({
      ...current,
      demoId,
      language: selected?.language || current.language,
      projectPath: selected?.project_path || "",
      bugReport: selected?.bug_report || current.bugReport,
    }));
  }

  async function onFileChange(fileList) {
    const normalized = await filesToPayload(fileList);
    setUploadedFiles(normalized);
    if (normalized.length) {
      setForm((current) => ({ ...current, language: inferLanguageFromFilename(normalized[0].filename) }));
    }
  }

  function onReset() {
    const nextForm = { ...createInitialForm(), demoId: demoProjects[0]?.id ?? "" };
    setForm(nextForm);
    setUploadedFiles([]);
    setResult(null);
    setTimeline([]);
    setElapsedSeconds(0);
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  }

  async function onRun() {
    if (!form.bugReport.trim()) {
      setResult({ status: "failed", final_summary: "Add a bug report before running the workflow." });
      return;
    }

    if (form.mode === "custom" && uploadedFiles.length === 0) {
      setResult({ status: "failed", final_summary: "Upload at least one source file in Custom Upload mode." });
      return;
    }

    setRunning(true);
    setElapsedSeconds(0);
    setTimeline([]);
    try {
      const payload =
        form.mode === "demo"
          ? {
              bug_report: form.bugReport,
              project_path: form.projectPath,
              language: form.language,
              fast_mode: form.fastMode,
              execution_mode: form.executionMode,
            }
          : {
              bug_report: form.bugReport,
              language: form.language,
              fast_mode: form.fastMode,
              execution_mode: form.executionMode,
              custom_files: uploadedFiles,
            };

      const workflowResult = await api.runWorkflow(payload);
      setResult(workflowResult);
      if (workflowResult.run_id) {
        try {
          const entries = await api.timeline(workflowResult.run_id);
          setTimeline(entries);
        } catch {
          setTimeline([]);
        }
      }
    } catch (error) {
      setResult({ status: "failed", final_summary: error.message });
      setTimeline([]);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="page-shell">
      <AppHeader onClearData={onReset} />
      <main className="dashboard-grid">
        <div className="left-column">
          <RunConfigurationPanel
            apiReady={apiReady}
            form={form}
            demoProjects={demoProjects}
            uploadedFiles={uploadedFiles}
            running={running}
            onModeChange={onModeChange}
            onFieldChange={onFieldChange}
            onDemoChange={onDemoChange}
            onFileChange={onFileChange}
            onRun={onRun}
            onReset={onReset}
          />
        </div>
        <div className="right-column">
          <ExecutionSummaryPanel result={result} running={running} elapsedSeconds={elapsedSeconds} plannedExecutionMode={form.executionMode} />
          <div className="agents-grid">
            <ClassifierAgentPanel result={result} />
            <RootCauseAgentPanel result={result} />
            <FixGeneratorAgentPanel result={result} />
            <TesterAgentPanel result={result} />
          </div>
          <TimelinePanel timeline={timeline} />
          <ArtifactsPanel result={result} reportUrl={reportUrl} patchUrl={patchUrl} rawJsonUrl={rawJsonUrl} />
          <RawResultPanel result={result} />
        </div>
      </main>
    </div>
  );
}
