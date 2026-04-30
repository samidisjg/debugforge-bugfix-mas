# Architecture Overview

## Problem Domain
The project automates software bug fixing for localized defects in source code, including arithmetic, logic, and concurrency-related bugs.

## Multi-Agent Workflow
1. Bug Classifier Agent receives the bug report.
2. Root Cause Agent searches the codebase and extracts evidence.
3. Fix Generator Agent creates a backup and applies a patch.
4. Tester Agent validates the fix, performs rollback if needed, and writes the final execution report.

## Shared State
The global state includes:
- run_id
- bug_report
- project_path
- language
- source_extensions
- test_command
- classification
- search_matches
- root_cause
- patch
- test_results
- final_report_path
- final_summary

## Tools By Member
- Member 1: bug report parser
- Member 2: source search and concurrency risk scanner
- Member 3: backup, patch write, restore
- Member 4: language-aware test runner and final report writer

## Observability
Every agent writes JSONL logs containing:
- run_id
- agent name
- input
- tool_calls
- output

## Reliability Features
- structured shared state
- backup before patching
- rollback on failed validation
- final markdown report per run
