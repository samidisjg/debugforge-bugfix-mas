const API_BASE = import.meta.env.VITE_API_BASE ?? "";
const DEFAULT_TIMEOUT_MS = 30000;
const RUN_WORKFLOW_TIMEOUT_MS = 310000;

async function request(path, options = {}) {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, ...fetchOptions } = options;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API_BASE}${path}`, { ...fetchOptions, signal: controller.signal });
    const contentType = response.headers.get("content-type") ?? "";
    const payload = contentType.includes("application/json") ? await response.json() : await response.text();

    if (!response.ok) {
      const detail = typeof payload === "object" && payload !== null ? payload.detail : payload;
      throw new Error(detail || "Request failed.");
    }

    return payload;
  } catch (error) {
    if (error?.name === "AbortError") {
      throw new Error(
        `Request timed out after ${Math.floor(timeoutMs / 1000)}s. Local Ollama runs can take several minutes; try Fast Mode or use a more specific bug report if this persists.`,
      );
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

export const api = {
  health: () => request("/api/health"),
  demoProjects: () => request("/api/demo-projects"),
  runWorkflow: (body) =>
    request("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      timeoutMs: RUN_WORKFLOW_TIMEOUT_MS,
    }),
  timeline: (runId) => request(`/api/timeline/${runId}`),
};

export function buildReportPdfUrl(runId) {
  return `${API_BASE}/api/report-pdf/${runId}`;
}

export function buildPatchUrl(runId) {
  return `${API_BASE}/api/patch/${runId}`;
}
