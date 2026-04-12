"""Shared constants, paths, and type definitions."""

from pathlib import Path
from typing import TypedDict, NamedTuple

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills"
EVALS_DIR = ROOT / "evals" / "cases"
CHECKS_DIR = ROOT / "evals" / "checks"
RESULTS_DIR = ROOT / "results"


class CaseConfig(TypedDict):
    id: str
    name: str
    description: str
    skill: str


class PromptConfig(TypedDict):
    text: str


class RubricConfig(TypedDict):
    criteria: list[str]


class ChecksConfig(TypedDict, total=False):
    scripts: list[str]
    linters: list[str]


class OptionsConfig(TypedDict, total=False):
    model: str
    max_budget_usd: float


class RunResult(NamedTuple):
    case_id: str
    variant: str  # "with_skill" or "baseline"
    raw_output: str
    model: str
    timestamp: str
    messages: list[dict]  # full stream-json messages for workflow analysis
    command: str = ""  # the claude command used to run this variant


class ScoreRow(TypedDict):
    case_id: str
    variant: str
    criterion: str
    score: int  # 0, 1, or 2
    explanation: str


class CheckRow(TypedDict):
    case_id: str
    variant: str
    check_name: str
    passed: bool
    detail: str
