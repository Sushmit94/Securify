from aggregator.merge_findings import merge
from backend.services.pipeline import _extract_functions
from language_support.detector import LanguageDetector
from language_support.parsers import python_parser


def _static_finding(**overrides):
    base = {
        "line": 10,
        "end_line": 10,
        "type": "SQL Injection",
        "cwe": "CWE-89",
        "severity": "high",
        "confidence": 0.7,
        "source": "static_analysis",
        "rule_id": "python-sql-injection-string-format",
        "function_name": None,
        "explanation": "concatenated SQL",
        "suggested_fix": None,
        "file": "app.py",
    }
    base.update(overrides)
    return base


def _llm_finding(**overrides):
    base = {
        "line": 10,
        "end_line": 10,
        "type": "SQL Injection",
        "cwe": "CWE-89",
        "severity": "high",
        "confidence": 0.9,
        "source": "llm_reasoning",
        "rule_id": "python-sql-injection-string-format",
        "function_name": None,
        "explanation": "confirmed: uid comes from request params",
        "suggested_fix": "use parameterized query",
        "file": "app.py",
        "llm_status": "confirmed",
    }
    base.update(overrides)
    return base


def test_merge_confirmed_finding_combines_sources():
    merged = merge([_static_finding()], [_llm_finding()])
    assert len(merged) == 1
    assert set(merged[0]["sources"]) == {"static_analysis", "llm_reasoning"}
    assert merged[0]["confidence"] > 0.7  # agreement bonus should push it above either layer alone


def test_merge_rejected_finding_is_dropped():
    rejected = _llm_finding(llm_status="rejected")
    merged = merge([_static_finding()], [rejected])
    assert merged == []


def test_merge_new_llm_finding_is_kept_standalone():
    new_finding = _llm_finding(line=42, rule_id=None, llm_status="new")
    merged = merge([], [new_finding])
    assert len(merged) == 1
    assert merged[0]["sources"] == ["llm_reasoning"]


def test_merge_applies_ml_score_within_function_range():
    ml_scores = [{"function_name": "get_user", "start_line": 8, "end_line": 12, "score": 0.9}]
    merged = merge([_static_finding()], [], ml_scores)
    assert "ml_classifier" in merged[0]["sources"]


def test_merge_ignores_low_ml_score():
    ml_scores = [{"function_name": "get_user", "start_line": 8, "end_line": 12, "score": 0.1}]
    merged = merge([_static_finding()], [], ml_scores)
    assert "ml_classifier" not in merged[0]["sources"]


def test_extract_functions_python():
    code = "def foo():\n    return 1\n\ndef bar():\n    return 2\n"
    units = _extract_functions("language_support.parsers.python_parser", code, "app.py")
    assert [u["name"] for u in units] == ["foo", "bar"]


def test_extract_functions_falls_back_on_bad_module_path():
    units = _extract_functions("language_support.parsers.does_not_exist", "print('hi')", "app.py")
    assert len(units) == 1
    assert units[0]["name"] == "<file>"


def test_language_detector_by_extension():
    detector = LanguageDetector(use_guesslang_fallback=False)
    assert detector.detect_snippet("print(1)", hint_filename="app.py") == "python"
    assert detector.detect_snippet("console.log(1)", hint_filename="app.js") == "javascript"


def test_python_parser_extracts_class_methods():
    code = "class Foo:\n    def bar(self):\n        return 1\n"
    units = python_parser.extract_functions(code)
    assert units[0]["name"] == "Foo.bar"
