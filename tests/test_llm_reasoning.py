from llm_reasoning import llm_client, prompt_templates, response_parser


def test_build_prompt_includes_code_and_language():
    prompt = prompt_templates.build_prompt(
        code="def f(): pass",
        language="python",
        file_path="app.py",
        static_findings=[],
        ml_score=0.8,
        function_name="f",
    )
    assert "def f(): pass" in prompt
    assert "python" in prompt
    assert "0.800" in prompt


def test_parse_response_handles_raw_json():
    raw = '{"findings": [{"line": 3, "type": "SQL Injection", "severity": "high", "confidence": 0.9, "status": "new", "explanation": "x", "suggested_fix": "y"}]}'
    findings = response_parser.parse_response(raw, "app.py")
    assert len(findings) == 1
    assert findings[0]["source"] == "llm_reasoning"
    assert findings[0]["llm_status"] == "new"
    assert findings[0]["severity"] == "high"


def test_parse_response_handles_markdown_fence():
    raw = '```json\n{"findings": [{"line": 1, "type": "XSS", "severity": "medium", "confidence": 0.5, "status": "confirmed", "upstream_rule_id": "js-innerhtml-assignment", "explanation": "x"}]}\n```'
    findings = response_parser.parse_response(raw, "app.js")
    assert len(findings) == 1
    assert findings[0]["rule_id"] == "js-innerhtml-assignment"


def test_parse_response_degrades_gracefully_on_garbage():
    assert response_parser.parse_response("not json at all", "app.py") == []


def test_parse_response_clamps_confidence_and_invalid_severity():
    raw = '{"findings": [{"line": 1, "type": "X", "severity": "apocalyptic", "confidence": 5, "status": "new", "explanation": "x"}]}'
    findings = response_parser.parse_response(raw, "app.py")
    assert findings[0]["severity"] == "medium"
    assert findings[0]["confidence"] == 1.0


def test_llm_client_is_available_reflects_env(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert llm_client.is_available() is False

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    assert llm_client.is_available() is True
