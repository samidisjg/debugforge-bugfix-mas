# Bug Fixing Assistant MAS

A locally hosted multi-agent system for CTSE Assignment 2. The system accepts a bug report, inspects a target project, proposes a fix, runs tests, and produces a final execution report.

## Team Design

- Agent 1: `Bug Classifier Agent`
- Agent 2: `Root Cause Agent`
- Agent 3: `Fix Generator Agent`
- Agent 4: `Tester Agent`

Each team member can own:
- one agent prompt/persona
- one custom Python tool
- one evaluation script

## Tech Stack

- `Ollama` for the local model
- `LangGraph` for orchestration
- `LangChain-Ollama` for model integration
- `Python` for tools and the shared control plane
- JSONL execution logs for observability

## Supported Languages

The orchestrator now supports:
- `Python`
- `JavaScript`
- `Java`
- `Go`

It also includes concurrency-bug support for Python-style race conditions through:
- concurrency-aware classification hints
- concurrency risk scanning
- root-cause evidence for shared-state updates and threading patterns
- a safe Python lock-based fallback patch for the sample race-condition project

## Project Structure

```text
src/bug_fixing_mas/
  classifier_agent/
    agent_classifier.py
    tool_bug_report_parser.py
  root_cause_agent/
    agent_root_cause.py
    tool_code_search.py
  fix_generator_agent/
    agent_fix_generator.py
    tool_patch_tool.py
  tester_agent/
    agent_tester.py
    tool_test_runner.py
    tool_final_report.py
  shared/
    state.py
    models.py
    logging_utils.py
    language_config.py
  graph.py
  main.py
sample_project/
sample_projects/
  python_concurrency/
  python_rollback_demo/
  python_validation/
  python_wrong_return/
  javascript/
  java/
  go/
frontend/
tests/
```

## Workflow

1. Read the bug report.
2. Detect or accept the target project language.
3. Classify the bug type and severity.
4. Search the target codebase for likely root causes.
5. For concurrency reports, scan for thread, lock, mutex, and shared-state risk patterns.
6. Generate a code patch suggestion.
7. Create a backup and apply the patch.
8. Run language-specific tests and summarize the outcome.
9. Roll back automatically if validation fails.
10. Write a final markdown execution report.

## Setup

1. Install Python dependencies:

```bash
pip install -e .
```

2. Install and start Ollama.

3. Pull a local model:

```bash
ollama pull llama3.1:8b
```

4. Run the default Python demo:

```bash
python -m bug_fixing_mas.main
```

5. Start the backend API and frontend UI together:

```bash
uvicorn bug_fixing_mas.api:app --reload
```

Then open `http://127.0.0.1:8000` in your browser. The backend serves the separate `frontend/` folder and exposes the API under `/api/*`.

6. Run the rollback demo:

```bash
python -m bug_fixing_mas.main --project-path sample_projects/python_rollback_demo --language python --bug-report-file sample_projects/python_rollback_demo/bug_report.txt
```

7. Run additional Python fixtures:

```bash
python -m bug_fixing_mas.main --project-path sample_projects/python_validation --language python --bug-report-file sample_projects/python_validation/bug_report.txt
python -m bug_fixing_mas.main --project-path sample_projects/python_wrong_return --language python --bug-report-file sample_projects/python_wrong_return/bug_report.txt
```


## Frontend Features

The separate `frontend/` folder provides:
- a `Custom Code` mode for pasted source code and optional tests
- a `Demo Project` mode for repeatable assignment demos
- editable bug report input without forcing a bug-type selection
- language, source filename, and optional test filename controls
- live MAS execution through the backend API
- evidence, final summary, and raw JSON output panels
- generated final report preview plus downloadable markdown report

## Default Test Commands

- Python: `python -m pytest -q`
- JavaScript: `npm test -- --runInBand`
- Java: `mvn test -q` or `gradlew test`
- Go: `go test ./...`

## Demo Scenario

The repository includes:
- a Python arithmetic bug demo in `sample_project/`
- a Python concurrency race-condition demo in `sample_projects/python_concurrency/`
- a Python rollback demonstration in `sample_projects/python_rollback_demo/`
- extra Python validation and wrong-return fixtures in `sample_projects/python_validation/` and `sample_projects/python_wrong_return/`
- additional JavaScript, Java, and Go sample projects in `sample_projects/`

## Evaluation

Run the unified evaluation harness with:

```bash
python tests/run_all_evaluations.py
```

## Team Ownership

- IT22603418 P Pradicksha: `src/bug_fixing_mas/classifier_agent/`
- IT22577160 Nimes R H R: `src/bug_fixing_mas/root_cause_agent/`
- IT22602978 Daminidu T W T: `src/bug_fixing_mas/fix_generator_agent/`
- IT22607232 Gamage S S J: `src/bug_fixing_mas/tester_agent/`
