from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from bug_fixing_mas.tester_agent.tool_final_report import write_final_report_pdf
from bug_fixing_mas.service import DEFAULT_BUG_REPORT, run_bug_fixing_workflow


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
FRONTEND_DIST_DIR = FRONTEND_DIR / "dist"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"
LOGS_DIR = PROJECT_ROOT / "logs"
AGENT_LOG_PATH = LOGS_DIR / "agent_runs.jsonl"
RUN_TIMEOUT_SECONDS = int(os.getenv("BUG_FIXING_RUN_TIMEOUT_SECONDS", "300"))
RUN_EXECUTOR = ThreadPoolExecutor(max_workers=4)


class CustomFileInput(BaseModel):
    """A single uploaded or pasted file for custom workspace runs."""

    filename: str = Field(min_length=1, description="Relative filename inside the temporary project workspace.")
    content: str = Field(description="Full file contents.")


class RunWorkflowRequest(BaseModel):
    """Request body for running the MAS workflow."""

    bug_report: str = Field(min_length=1, description="The bug report to analyze.")
    project_path: str | None = Field(default=None, description="Optional target project path.")
    language: str | None = Field(default=None, description="Optional explicit language selection.")
    log_path: str | None = Field(default=None, description="Optional log output path.")
    fast_mode: bool = Field(default=False, description="Use heuristic-first fast mode for quicker local runs.")
    execution_mode: str = Field(default="full", description="Execution mode: full, classifier, root_cause, fix_generator, or tester.")
    custom_source_code: str | None = Field(default=None, description="Optional pasted source code.")
    custom_source_filename: str | None = Field(default=None, description="Optional source filename for pasted code.")
    custom_test_code: str | None = Field(default=None, description="Optional pasted automated test code.")
    custom_test_filename: str | None = Field(default=None, description="Optional test filename for pasted code.")
    custom_files: list[CustomFileInput] = Field(default_factory=list, description="Optional list of uploaded custom files.")


app = FastAPI(title="Bug Fixing MAS API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS_DIR), name="frontend-assets")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/demo-projects")
def demo_projects() -> list[dict[str, str | None]]:
    return [
        {
            "id": "python-arithmetic",
            "label": "Python Arithmetic Bug",
            "project_path": str(PROJECT_ROOT / "sample_project"),
            "language": "python",
            "bug_report": DEFAULT_BUG_REPORT,
            "bug_report_file": None,
        },
        {
            "id": "python-concurrency",
            "label": "Python Concurrency Bug",
            "project_path": str(PROJECT_ROOT / "sample_projects" / "python_concurrency"),
            "language": "python",
            "bug_report": (PROJECT_ROOT / "sample_projects" / "python_concurrency" / "bug_report.txt").read_text(encoding="utf-8"),
            "bug_report_file": str(PROJECT_ROOT / "sample_projects" / "python_concurrency" / "bug_report.txt"),
        },
        {
            "id": "python-rollback",
            "label": "Python Rollback Demo",
            "project_path": str(PROJECT_ROOT / "sample_projects" / "python_rollback_demo"),
            "language": "python",
            "bug_report": (PROJECT_ROOT / "sample_projects" / "python_rollback_demo" / "bug_report.txt").read_text(encoding="utf-8"),
            "bug_report_file": str(PROJECT_ROOT / "sample_projects" / "python_rollback_demo" / "bug_report.txt"),
        },
        {
            "id": "python-validation",
            "label": "Python Validation Bug",
            "project_path": str(PROJECT_ROOT / "sample_projects" / "python_validation"),
            "language": "python",
            "bug_report": (PROJECT_ROOT / "sample_projects" / "python_validation" / "bug_report.txt").read_text(encoding="utf-8"),
            "bug_report_file": str(PROJECT_ROOT / "sample_projects" / "python_validation" / "bug_report.txt"),
        },
        {
            "id": "python-wrong-return",
            "label": "Python Wrong Return Bug",
            "project_path": str(PROJECT_ROOT / "sample_projects" / "python_wrong_return"),
            "language": "python",
            "bug_report": (PROJECT_ROOT / "sample_projects" / "python_wrong_return" / "bug_report.txt").read_text(encoding="utf-8"),
            "bug_report_file": str(PROJECT_ROOT / "sample_projects" / "python_wrong_return" / "bug_report.txt"),
        },
        {
            "id": "javascript-arithmetic",
            "label": "JavaScript Bug",
            "project_path": str(PROJECT_ROOT / "sample_projects" / "javascript"),
            "language": "javascript",
            "bug_report": DEFAULT_BUG_REPORT,
            "bug_report_file": None,
        },
        {
            "id": "go-arithmetic",
            "label": "Go Bug",
            "project_path": str(PROJECT_ROOT / "sample_projects" / "go"),
            "language": "go",
            "bug_report": DEFAULT_BUG_REPORT,
            "bug_report_file": None,
        },
        {
            "id": "java-arithmetic",
            "label": "Java Bug",
            "project_path": str(PROJECT_ROOT / "sample_projects" / "java"),
            "language": "java",
            "bug_report": DEFAULT_BUG_REPORT,
            "bug_report_file": None,
        },
    ]


@app.post("/api/run")
def run_workflow(payload: RunWorkflowRequest) -> dict[str, object]:
    future = None
    try:
        future = RUN_EXECUTOR.submit(
            run_bug_fixing_workflow,
            project_root=PROJECT_ROOT,
            bug_report=payload.bug_report,
            project_path=payload.project_path,
            log_path=payload.log_path,
            language=payload.language,
            fast_mode=payload.fast_mode,
            execution_mode=payload.execution_mode,
            custom_source_code=payload.custom_source_code,
            custom_source_filename=payload.custom_source_filename,
            custom_test_code=payload.custom_test_code,
            custom_test_filename=payload.custom_test_filename,
            custom_files=[file_info.model_dump() for file_info in payload.custom_files],
        )
        return future.result(timeout=RUN_TIMEOUT_SECONDS)
    except FuturesTimeoutError as exc:
        if future is not None:
            future.cancel()
        raise HTTPException(
            status_code=504,
            detail=f"Workflow timed out after {RUN_TIMEOUT_SECONDS}s. Verify Ollama is running and try a more specific bug report.",
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/timeline/{run_id}")
def run_timeline(run_id: str) -> list[dict[str, object]]:
    if not AGENT_LOG_PATH.exists():
        return []
    entries: list[dict[str, object]] = []
    with AGENT_LOG_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            payload = json.loads(line)
            if payload.get("run_id") == run_id:
                entries.append(
                    {
                        "timestamp": payload.get("timestamp"),
                        "agent": payload.get("agent"),
                        "status": payload.get("status"),
                        "duration_ms": payload.get("duration_ms"),
                        "tool_calls": payload.get("tool_calls", []),
                    }
                )
    return entries


@app.get("/api/report/{run_id}")
def download_report(run_id: str) -> FileResponse:
    report_path = LOGS_DIR / f"final_report_{run_id}.md"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found.")
    return FileResponse(report_path, media_type="text/markdown", filename=report_path.name)


@app.get("/api/report-pdf/{run_id}")
def download_report_pdf(run_id: str) -> FileResponse:
    report_path = LOGS_DIR / f"final_report_{run_id}.pdf"
    if not report_path.exists():
        markdown_path = LOGS_DIR / f"final_report_{run_id}.md"
        if not markdown_path.exists():
            raise HTTPException(status_code=404, detail="PDF report not found.")
        markdown_content = markdown_path.read_text(encoding="utf-8")
        write_final_report_pdf(str(report_path), markdown_content)
    return FileResponse(report_path, media_type="application/pdf", filename=report_path.name)


@app.get("/api/patch/{run_id}")
def download_patch(run_id: str) -> PlainTextResponse:
    diff_path = LOGS_DIR / f"patch_{run_id}.diff"
    if not diff_path.exists():
        raise HTTPException(status_code=404, detail="Patch diff not found.")
    return PlainTextResponse(diff_path.read_text(encoding="utf-8"), media_type="text/plain")


@app.get("/", response_model=None)
def frontend_index() -> Response:
    index_path = FRONTEND_DIST_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return PlainTextResponse(
        "React frontend is not built yet. Run `cd frontend && npm install && npm run build` or use `npm run dev` for the Vite frontend.",
        status_code=503,
    )
