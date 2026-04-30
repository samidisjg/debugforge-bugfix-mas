from bug_fixing_mas.root_cause_agent.agent_root_cause import root_cause_agent, _ground_root_cause_output


def test_root_cause_prefers_source_file_for_concurrency_bug() -> None:
    state = {
        "run_id": "root-cause-demo",
        "bug_report": "Race condition in threaded counter update.",
        "project_path": "sample_projects/python_concurrency",
        "language": "python",
        "source_extensions": [".py"],
        "test_command": ["python", "-m", "pytest", "-q"],
        "execution_log_path": "logs/test_root_cause.jsonl",
        "classification": {
            "bug_type": "Concurrency Bug",
            "severity": "Medium",
            "summary": "Missing lock around shared-state mutation in counter module.",
            "likely_modules": ["counter"],
        },
        "status": "classified",
    }
    updated = root_cause_agent(state)
    assert updated["root_cause"]["suspected_file"] == "counter.py"
    assert updated["root_cause"]["evidence"]


def test_root_cause_grounding_replaces_hallucinated_file_and_evidence() -> None:
    matches = [
        {
            "file": "sample_projects/python_concurrency/counter.py",
            "term": "thread",
            "line_number": 9,
            "snippet": "current = self.value",
            "is_test_file": False,
            "score": 12,
            "context": ["def increment(self) -> None:", "current = self.value"],
        }
    ]
    hallucinated = {
        "suspected_file": "non_existent.py",
        "suspected_function": "",
        "evidence": ["fake.py:10 -> invented signal"],
        "reasoning": "unverified",
        "confidence": 1.6,
    }
    grounded = _ground_root_cause_output(hallucinated, matches, "sample_projects/python_concurrency")
    assert grounded["suspected_file"] == "counter.py"
    assert grounded["suspected_function"] != ""
    assert "counter.py" in grounded["evidence"][0]
    assert 0.0 <= grounded["confidence"] <= 1.0
