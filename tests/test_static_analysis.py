from static_analysis import bandit_runner, semgrep_runner


def test_semgrep_to_finding_maps_common_shape():
    raw = {
        "check_id": "python-sql-injection-string-format",
        "start": {"line": 10},
        "end": {"line": 10},
        "extra": {
            "message": "SQL injection via string formatting",
            "severity": "ERROR",
            "metadata": {"cwe": ["CWE-89"], "vulnerability_class": ["SQL Injection"]},
        },
    }
    finding = semgrep_runner._to_finding(raw, "app.py")

    assert finding["line"] == 10
    assert finding["cwe"] == "CWE-89"
    assert finding["severity"] == "high"
    assert finding["source"] == "static_analysis"
    assert finding["rule_id"] == "python-sql-injection-string-format"
    assert finding["file"] == "app.py"


def test_semgrep_run_returns_empty_when_not_installed(monkeypatch):
    monkeypatch.setattr(semgrep_runner, "is_available", lambda: False)
    assert semgrep_runner.run("app.py", "python") == []


def test_bandit_to_finding_maps_severity_and_confidence():
    raw = {
        "test_id": "B608",
        "test_name": "hardcoded_sql_expressions",
        "line_number": 5,
        "issue_severity": "HIGH",
        "issue_confidence": "HIGH",
        "issue_text": "Possible SQL injection",
        "issue_cwe": None,
    }
    finding = bandit_runner._to_finding(raw, "app.py")

    assert finding["line"] == 5
    assert finding["severity"] == "high"
    assert finding["confidence"] == 0.85
    assert finding["cwe"] == "CWE-89"
    assert finding["source"] == "static_analysis"


def test_bandit_run_returns_empty_when_not_installed(monkeypatch):
    monkeypatch.setattr(bandit_runner, "is_available", lambda: False)
    assert bandit_runner.run("app.py") == []
