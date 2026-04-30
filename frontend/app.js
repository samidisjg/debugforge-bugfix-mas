const inputModeSelect = document.getElementById("inputModeSelect");
const demoSection = document.getElementById("demoSection");
const customSection = document.getElementById("customSection");
const demoSelect = document.getElementById("demoSelect");
const languageSelect = document.getElementById("languageSelect");
const projectPathInput = document.getElementById("projectPathInput");
const sourceFilenameInput = document.getElementById("sourceFilenameInput");
const testFilenameInput = document.getElementById("testFilenameInput");
const fileUploadInput = document.getElementById("fileUploadInput");
const uploadDropzone = document.getElementById("uploadDropzone");
const clearUploadsButton = document.getElementById("clearUploadsButton");
const uploadCountLabel = document.getElementById("uploadCountLabel");
const uploadedFilesList = document.getElementById("uploadedFilesList");
const sourceCodeInput = document.getElementById("sourceCodeInput");
const testCodeInput = document.getElementById("testCodeInput");
const bugReportInput = document.getElementById("bugReportInput");
const runButton = document.getElementById("runButton");
const loadDemoButton = document.getElementById("loadDemoButton");
const healthBadge = document.getElementById("healthBadge");
const runStatus = document.getElementById("runStatus");
const runHint = document.getElementById("runHint");
const runIdValue = document.getElementById("runIdValue");
const bugTypeValue = document.getElementById("bugTypeValue");
const rootCauseValue = document.getElementById("rootCauseValue");
const testsValue = document.getElementById("testsValue");
const finalSummaryText = document.getElementById("finalSummaryText");
const evidenceList = document.getElementById("evidenceList");
const timelineList = document.getElementById("timelineList");
const reportLink = document.getElementById("reportLink");
const patchLink = document.getElementById("patchLink");
const reportPreview = document.getElementById("reportPreview");
const jsonOutput = document.getElementById("jsonOutput");

let demoProjects = [];
let runTimerId = null;
let runStartedAt = null;
let uploadedFiles = [];
const RUN_REQUEST_TIMEOUT_MS = 130000;

function updateCustomFieldHints() {
  sourceFilenameInput.placeholder = `${inferDefaultFilename(languageSelect.value)} (optional)`;
  testFilenameInput.placeholder = `${inferDefaultTestFilename(languageSelect.value)} (optional)`;
}

function resetCustomInputs() {
  sourceFilenameInput.value = "";
  testFilenameInput.value = "";
  sourceCodeInput.value = "";
  testCodeInput.value = "";
  bugReportInput.value = "";
  setUploadedFiles([]);
  updateCustomFieldHints();
}

function setPill(element, text, kind) {
  element.textContent = text;
  element.className = `status-pill ${kind}`;
}

function formatElapsed(ms) {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

function formatDuration(ms) {
  if (typeof ms !== "number") return "-";
  return `${ms.toFixed(0)} ms`;
}

function stopRunTimer() {
  if (runTimerId) {
    clearInterval(runTimerId);
    runTimerId = null;
  }
  runStartedAt = null;
}

function startRunTimer() {
  stopRunTimer();
  runStartedAt = Date.now();
  runHint.textContent = "The local Ollama model is working. First runs can take around 1-2 minutes.";
  timelineList.innerHTML = "<li>No agent activity yet.</li>";
  runTimerId = setInterval(() => {
    const elapsed = formatElapsed(Date.now() - runStartedAt);
    setPill(runStatus, `Running ${elapsed}`, "running");
  }, 1000);
}

function toggleModeSections() {
  const isCustom = inputModeSelect.value === "custom";
  customSection.classList.toggle("hidden-section", !isCustom);
  demoSection.classList.toggle("hidden-section", isCustom);
  loadDemoButton.textContent = isCustom ? "Load Sample Code" : "Load Demo Defaults";
}

function getSelectedDemo() {
  return demoProjects.find((project) => project.id === demoSelect.value) ?? demoProjects[0];
}

function inferDefaultFilename(language) {
  return {
    python: "main.py",
    javascript: "main.js",
    java: "Main.java",
    go: "main.go",
  }[language] ?? "main.py";
}

function inferDefaultTestFilename(language) {
  return {
    python: "test_main.py",
    javascript: "main.test.js",
    java: "MainTest.java",
    go: "main_test.go",
  }[language] ?? "test_main.py";
}

function getDefaultCustomTemplate(language) {
  const templates = {
    python: {
      sourceFilename: "calculator.py",
      testFilename: "test_calculator.py",
      sourceCode: `def add(a: float, b: float) -> float:\n    return a + b\n\n\ndef divide(a: float, b: float) -> float:\n    if b == 0:\n        return 0\n    return a / b\n`,
      testCode: `import pytest\nfrom calculator import add, divide\n\n\ndef test_add() -> None:\n    assert add(2, 3) == 5\n\n\ndef test_divide() -> None:\n    assert divide(10, 2) == 5\n\n\ndef test_divide_by_zero() -> None:\n    with pytest.raises(ZeroDivisionError):\n        divide(5, 0)\n`,
      bugReport: `Division by zero is returning 0 instead of raising an error.\nUsers expect ZeroDivisionError for divide(5, 0).\nThe failing behavior is in the calculator utility.`,
    },
    javascript: {
      sourceFilename: "main.js",
      testFilename: "",
      sourceCode: `function divide(a, b) {\n  if (b === 0) {\n    return 0;\n  }\n  return a / b;\n}\n\nmodule.exports = { divide };\n`,
      testCode: "",
      bugReport: "Division by zero should not silently return 0. The function should signal an error or guard invalid input.",
    },
    java: {
      sourceFilename: "Main.java",
      testFilename: "",
      sourceCode: `public class Main {\n    public static int divide(int a, int b) {\n        if (b == 0) {\n            return 0;\n        }\n        return a / b;\n    }\n}\n`,
      testCode: "",
      bugReport: "Division by zero is returning 0 instead of throwing an arithmetic-related exception.",
    },
    go: {
      sourceFilename: "main.go",
      testFilename: "",
      sourceCode: `package main\n\nfunc divide(a int, b int) int {\n    if b == 0 {\n        return 0\n    }\n    return a / b\n}\n`,
      testCode: "",
      bugReport: "Division by zero is returning 0 and hiding the bug instead of failing loudly.",
    },
  };
  return templates[language] ?? templates.python;
}

function setUploadedFiles(files) {
  uploadedFiles = files;
  uploadCountLabel.textContent = `${uploadedFiles.length} file${uploadedFiles.length === 1 ? "" : "s"}`;
  if (uploadedFiles.length === 0) {
    uploadedFilesList.innerHTML = "<li>No uploaded files yet.</li>";
    return;
  }
  uploadedFilesList.innerHTML = uploadedFiles
    .map((file) => `<li><strong>${file.filename}</strong><span>${file.content.split(/\r?\n/).length} lines</span></li>`)
    .join("");
}

async function normalizeIncomingFiles(fileList) {
  return Promise.all(
    Array.from(fileList ?? []).map(async (file) => ({
      filename: file.webkitRelativePath || file.name,
      content: await file.text(),
    }))
  );
}

async function handleFileUpload(event) {
  const files = await normalizeIncomingFiles(event.target.files ?? []);
  setUploadedFiles(files);
}

function clearUploadedFiles() {
  fileUploadInput.value = "";
  setUploadedFiles([]);
}

function applyDemoSelection() {
  const demo = getSelectedDemo();
  if (!demo) return;
  languageSelect.value = demo.language;
  projectPathInput.value = demo.project_path;
  bugReportInput.value = demo.bug_report;
}

function applyCustomTemplate() {
  const template = getDefaultCustomTemplate(languageSelect.value);
  sourceFilenameInput.value = template.sourceFilename;
  testFilenameInput.value = template.testFilename || inferDefaultTestFilename(languageSelect.value);
  sourceCodeInput.value = template.sourceCode;
  testCodeInput.value = template.testCode;
  bugReportInput.value = template.bugReport;
  setUploadedFiles([]);
  updateCustomFieldHints();
}

function renderEvidence(evidence = []) {
  if (!Array.isArray(evidence) || evidence.length === 0) {
    evidenceList.innerHTML = "<li>No evidence recorded.</li>";
    return;
  }
  evidenceList.innerHTML = evidence.map((item) => `<li>${item}</li>`).join("");
}

function renderTimeline(entries = []) {
  if (!Array.isArray(entries) || entries.length === 0) {
    timelineList.innerHTML = "<li>No agent activity yet.</li>";
    return;
  }
  timelineList.innerHTML = entries.map((entry) => {
    const tools = Array.isArray(entry.tool_calls) ? entry.tool_calls.map((tool) => tool.tool).join(", ") : "";
    const toolSuffix = tools ? ` ? ${tools}` : "";
    return `<li><strong>${entry.agent}</strong><span>${entry.status} ? ${formatDuration(entry.duration_ms)}${toolSuffix}</span></li>`;
  }).join("");
}

async function loadTimeline(runId) {
  try {
    const response = await fetch(`/api/timeline/${encodeURIComponent(runId)}`);
    if (!response.ok) {
      renderTimeline([]);
      return;
    }
    const entries = await response.json();
    renderTimeline(entries);
  } catch {
    renderTimeline([]);
  }
}

function renderResult(result) {
  stopRunTimer();
  runIdValue.textContent = result.run_id ?? "-";
  bugTypeValue.textContent = result.classification?.bug_type ?? "-";
  rootCauseValue.textContent = `${result.root_cause?.suspected_file ?? "-"} / ${result.root_cause?.suspected_function ?? "-"}`;
  if (result.test_results?.validation_skipped) {
    testsValue.textContent = "Skipped";
  } else {
    testsValue.textContent = result.test_results?.passed ? "Passed" : `${result.status ?? "Unknown"}`;
  }
  finalSummaryText.textContent = result.final_summary ?? "No summary returned.";
  runHint.textContent = `Completed with status: ${result.status ?? "finished"}.`;
  renderEvidence(result.root_cause?.evidence ?? []);
  reportPreview.textContent = result.final_report_markdown ?? "No report generated.";
  jsonOutput.textContent = JSON.stringify(result, null, 2);

  if (result.run_id) {
    reportLink.classList.remove("disabled");
    reportLink.href = `/api/report/${encodeURIComponent(result.run_id)}`;
    reportLink.setAttribute("download", `final_report_${result.run_id}.md`);
    patchLink.classList.remove("disabled");
    patchLink.href = `/api/patch/${encodeURIComponent(result.run_id)}`;
    patchLink.setAttribute("download", `patch_${result.run_id}.diff`);
    loadTimeline(result.run_id);
  } else {
    reportLink.classList.add("disabled");
    reportLink.href = "#";
    patchLink.classList.add("disabled");
    patchLink.href = "#";
    renderTimeline([]);
  }

  if (result.status === "tested") {
    setPill(runStatus, "Run Succeeded", "success");
  } else if (result.status === "rolled_back") {
    setPill(runStatus, "Rolled Back", "error");
  } else {
    setPill(runStatus, result.status ?? "Finished", "idle");
  }
}

async function fetchHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) throw new Error("Health check failed");
    setPill(healthBadge, "API Ready", "success");
  } catch {
    setPill(healthBadge, "API Offline", "error");
  }
}

async function loadDemoProjects() {
  const response = await fetch("/api/demo-projects");
  demoProjects = await response.json();
  demoSelect.innerHTML = demoProjects
    .map((project) => `<option value="${project.id}">${project.label}</option>`)
    .join("");
  applyDemoSelection();
}

function buildPayload() {
  const isCustom = inputModeSelect.value === "custom";
  return {
    bug_report: bugReportInput.value.trim(),
    project_path: isCustom ? null : (projectPathInput.value.trim() || null),
    language: languageSelect.value || null,
    log_path: null,
    custom_source_code: isCustom ? (sourceCodeInput.value.trim() || null) : null,
    custom_source_filename: isCustom ? (sourceFilenameInput.value.trim() || inferDefaultFilename(languageSelect.value)) : null,
    custom_test_code: isCustom ? (testCodeInput.value.trim() || null) : null,
    custom_test_filename: isCustom ? (testFilenameInput.value.trim() || inferDefaultTestFilename(languageSelect.value)) : null,
    custom_files: isCustom ? uploadedFiles : [],
  };
}

async function runWorkflow() {
  const payload = buildPayload();
  if (!payload.bug_report) {
    setPill(runStatus, "Missing Bug Report", "error");
    runHint.textContent = "Add a bug report before running the MAS.";
    return;
  }
  if (inputModeSelect.value === "custom" && !payload.custom_source_code && payload.custom_files.length === 0) {
    setPill(runStatus, "Missing Code", "error");
    runHint.textContent = "Paste source code or upload files in Custom Code mode before running the MAS.";
    return;
  }

  startRunTimer();
  runButton.disabled = true;
  loadDemoButton.disabled = true;
  inputModeSelect.disabled = true;
  clearUploadsButton.disabled = true;

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), RUN_REQUEST_TIMEOUT_MS);
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || "Backend request failed");
    }
    renderResult(result);
  } catch (error) {
    stopRunTimer();
    setPill(runStatus, "Run Failed", "error");
    const isTimeout = error?.name === "AbortError";
    const message = isTimeout
      ? "Request timed out. The backend took too long to respond."
      : (error.message || "Backend request failed");
    runHint.textContent = isTimeout
      ? "Request timed out. Try a more specific bug report or verify the backend logs."
      : "The backend returned an error. Check the message below.";
    finalSummaryText.textContent = message;
    jsonOutput.textContent = JSON.stringify({ error: message }, null, 2);
  } finally {
    runButton.disabled = false;
    loadDemoButton.disabled = false;
    inputModeSelect.disabled = false;
    clearUploadsButton.disabled = false;
  }
}

function wireDropzone() {
  const activeClass = "dropzone-active";
  ["dragenter", "dragover"].forEach((eventName) => {
    uploadDropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      uploadDropzone.classList.add(activeClass);
    });
  });
  ["dragleave", "drop"].forEach((eventName) => {
    uploadDropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      uploadDropzone.classList.remove(activeClass);
    });
  });
  uploadDropzone.addEventListener("drop", async (event) => {
    const files = await normalizeIncomingFiles(event.dataTransfer?.files ?? []);
    setUploadedFiles(files);
  });
}

inputModeSelect.addEventListener("change", toggleModeSections);
demoSelect.addEventListener("change", applyDemoSelection);
languageSelect.addEventListener("change", () => {
  if (inputModeSelect.value === "custom") {
    updateCustomFieldHints();
  }
});
loadDemoButton.addEventListener("click", () => {
  if (inputModeSelect.value === "custom") {
    applyCustomTemplate();
  } else {
    applyDemoSelection();
  }
});
fileUploadInput.addEventListener("change", handleFileUpload);
clearUploadsButton.addEventListener("click", clearUploadedFiles);
runButton.addEventListener("click", runWorkflow);

fetchHealth();
loadDemoProjects();
toggleModeSections();
resetCustomInputs();
wireDropzone();
renderTimeline([]);
