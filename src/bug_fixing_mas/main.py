from __future__ import annotations

import argparse
import json
from pathlib import Path

from bug_fixing_mas.service import DEFAULT_BUG_REPORT, run_bug_fixing_workflow


def main() -> None:
    """Run the end-to-end demo against a target project."""
    parser = argparse.ArgumentParser(description="Run the Bug Fixing MAS demo.")
    parser.add_argument("--bug-report-file", help="Optional text file containing the bug report.")
    parser.add_argument("--project-path", help="Optional target project path.")
    parser.add_argument("--log-path", help="Optional JSONL log output path.")
    parser.add_argument("--language", choices=["python", "javascript", "java", "go"], help="Optional explicit project language.")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    bug_report = DEFAULT_BUG_REPORT
    if args.bug_report_file:
        bug_report = Path(args.bug_report_file).read_text(encoding="utf-8")

    result = run_bug_fixing_workflow(
        project_root=project_root,
        bug_report=bug_report,
        project_path=args.project_path,
        log_path=args.log_path,
        language=args.language,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
