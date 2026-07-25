"""Maps a detected language to the pipeline components that should run for it.

This is the single source of truth for the tiered language-support strategy
described in the README: Tier 1 gets all three layers, Tier 2 skips the ML
classifier, Tier 3 (fallback) only gets LLM reasoning.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

_RULESETS_DIR = Path(__file__).resolve().parent.parent / "static_analysis" / "rulesets"
_CHECKPOINTS_DIR = Path(__file__).resolve().parent.parent / "ml_model" / "checkpoints"


@dataclass(frozen=True)
class LanguageConfig:
    name: str
    tier: int
    semgrep_ruleset: str | None       # path to a local ruleset, or None to use semgrep's registry defaults
    semgrep_registry_config: str | None  # semgrep registry config string, used when no local ruleset exists
    ml_checkpoint_dir: Path | None    # directory holding a fine-tuned classifier checkpoint, if any
    parser_module: str | None         # dotted module path under language_support.parsers
    bandit_supported: bool = False
    extra: dict = field(default_factory=dict)

    @property
    def has_static_analysis(self) -> bool:
        return self.semgrep_ruleset is not None or self.semgrep_registry_config is not None or self.bandit_supported

    @property
    def has_ml_classifier(self) -> bool:
        return self.ml_checkpoint_dir is not None and self.ml_checkpoint_dir.exists() and any(
            self.ml_checkpoint_dir.iterdir()
        )


_REGISTRY: dict[str, LanguageConfig] = {
    "python": LanguageConfig(
        name="python",
        tier=1,
        semgrep_ruleset=str(_RULESETS_DIR / "python.yml"),
        semgrep_registry_config="p/python",
        ml_checkpoint_dir=_CHECKPOINTS_DIR / "python_model",
        parser_module="language_support.parsers.python_parser",
        bandit_supported=True,
    ),
    "java": LanguageConfig(
        name="java",
        tier=1,
        semgrep_ruleset=str(_RULESETS_DIR / "java.yml"),
        semgrep_registry_config="p/java",
        ml_checkpoint_dir=_CHECKPOINTS_DIR / "java_model",
        parser_module="language_support.parsers.java_parser",
    ),
    "c": LanguageConfig(
        name="c",
        tier=1,
        semgrep_ruleset=str(_RULESETS_DIR / "cpp.yml"),
        semgrep_registry_config="p/c",
        ml_checkpoint_dir=_CHECKPOINTS_DIR / "cpp_model",
        parser_module="language_support.parsers.cpp_parser",
    ),
    "cpp": LanguageConfig(
        name="cpp",
        tier=1,
        semgrep_ruleset=str(_RULESETS_DIR / "cpp.yml"),
        semgrep_registry_config="p/c",
        ml_checkpoint_dir=_CHECKPOINTS_DIR / "cpp_model",
        parser_module="language_support.parsers.cpp_parser",
    ),
    "javascript": LanguageConfig(
        name="javascript",
        tier=2,
        semgrep_ruleset=str(_RULESETS_DIR / "javascript.yml"),
        semgrep_registry_config="p/javascript",
        ml_checkpoint_dir=None,
        parser_module="language_support.parsers.js_parser",
    ),
    "typescript": LanguageConfig(
        name="typescript",
        tier=2,
        semgrep_ruleset=str(_RULESETS_DIR / "javascript.yml"),
        semgrep_registry_config="p/typescript",
        ml_checkpoint_dir=None,
        parser_module="language_support.parsers.js_parser",
    ),
    "go": LanguageConfig(
        name="go",
        tier=2,
        semgrep_ruleset=str(_RULESETS_DIR / "go.yml"),
        semgrep_registry_config="p/golang",
        ml_checkpoint_dir=None,
        parser_module=None,
    ),
    "php": LanguageConfig(
        name="php", tier=2, semgrep_ruleset=None, semgrep_registry_config="p/php",
        ml_checkpoint_dir=None, parser_module=None,
    ),
    "ruby": LanguageConfig(
        name="ruby", tier=2, semgrep_ruleset=None, semgrep_registry_config="p/ruby",
        ml_checkpoint_dir=None, parser_module=None,
    ),
    "csharp": LanguageConfig(
        name="csharp", tier=2, semgrep_ruleset=None, semgrep_registry_config="p/csharp",
        ml_checkpoint_dir=None, parser_module=None,
    ),
    "kotlin": LanguageConfig(
        name="kotlin", tier=2, semgrep_ruleset=None, semgrep_registry_config="p/kotlin",
        ml_checkpoint_dir=None, parser_module=None,
    ),
    "rust": LanguageConfig(
        name="rust", tier=2, semgrep_ruleset=None, semgrep_registry_config="p/rust",
        ml_checkpoint_dir=None, parser_module=None,
    ),
}

DEFAULT_FALLBACK = LanguageConfig(
    name="unknown",
    tier=3,
    semgrep_ruleset=None,
    semgrep_registry_config=None,
    ml_checkpoint_dir=None,
    parser_module="language_support.parsers.generic_fallback",
)


def get_language_config(language: str | None) -> LanguageConfig:
    """Returns the pipeline config for a language, or the Tier 3 fallback if unknown/unsupported."""
    if not language:
        return DEFAULT_FALLBACK
    return _REGISTRY.get(language.lower(), DEFAULT_FALLBACK)


def supported_languages() -> list[str]:
    return sorted(_REGISTRY.keys())


def tier_of(language: str | None) -> int:
    return get_language_config(language).tier
