from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=8000)
]
Short = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
OptionalText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=8000)]
Status = Literal["Open - with L1", "Open - with Engineering", "Closed"]
Action = Literal[
    "Continue L1 Investigation",
    "Ready for Resolution",
    "Engineering Escalation Recommended",
    "More Information Required",
    "Review Recorded Resolution",
    "Coordinate with Engineering",
]


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


ReturnOutcome = Literal[
    "Insufficient info - returned to L1", "Config issue - returned to L1"
]
ClosureOutcome = Literal[
    "Fixed", "Duplicate of known issue", "Not a bug - how-to", "Not reproducible"
]


class Patch(Config):
    return_outcome: ReturnOutcome | None = None
    assigned_agent: Short | None = None
    status: Status | None = None


class Note(Config):
    text: Text


class Resolution(Note):
    engineering_outcome: ClosureOutcome | None = None


class ArticleIn(Config):
    title: Short
    category: Short
    issue: Text
    steps: Text
    resolution: OptionalText = ""


class ArticleOut(ArticleIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    updated_at: datetime


CHECKS = [
    "Problem understood",
    "Basic troubleshooting completed",
    "Relevant information collected",
    "Reproduction steps documented where applicable",
    "Supporting evidence recorded",
]


class CheckIn(Config):
    checks: list[str] = Field(default_factory=list, max_length=5)
    results: dict[Short, Text] = Field(default_factory=dict, max_length=20)

    @model_validator(mode="after")
    def valid_checks(self):
        if not set(self.checks) <= set(CHECKS) or len(self.checks) != len(
            set(self.checks)
        ):
            raise ValueError("Invalid pre-escalation checks")
        return self


class HandoffEvidence(Config):
    error: OptionalText = ""
    reproduction: OptionalText = ""
    supporting_evidence: OptionalText = ""
    expected: OptionalText = ""
    reason: OptionalText = ""


class ReadinessItem(Config):
    label: str
    recorded: bool
    detail: str


class Readiness(Config):
    items: list[ReadinessItem]
    ready: bool
    summary: str


class Handoff(Config):
    issue_summary: Text
    actual_behaviour: Text
    expected_behaviour: Text
    troubleshooting_completed: Text
    results: Text
    missing_information: Text
    reason_for_escalation: Text


class Decision(Config):
    handoff: Handoff
    override_reason: OptionalText = ""


Items = Annotated[list[Short], Field(max_length=20)]


class Analysis(Config):
    problem_summary: Text
    problem_area: Short
    category: Short
    priority: str = ""
    confirmed_facts: Items
    possible_causes: Items
    troubleshooting: Items
    missing_information: Items
    next_step: str = ""
    recommended_action: Action
    customer_response: Text
    handoff: Handoff


class AnalysisOut(Config):
    source: Literal["Groq", "Predefined rules"]
    result: Analysis
    detail: str


class TicketOut(BaseModel):
    model_config = ConfigDict(extra="allow")
    ticket_id: str
    client_name: str
    category: str
    description: str
    priority: str
    status: Status
    created_at: str
    escalated_to_eng: str
    assigned_agent: str
    reopen_count: int
    csat_score: int | None


class TicketPage(BaseModel):
    items: list[TicketOut]
    total: int
    page: int
    pages: int


class Metrics(Config):
    client_count: int
    engineering_open: int
    returned: int
    returned_rate: float | None
    total: int
    open: int
    resolved: int
    escalated: int
    reopened: int
    escalation_rate: float | None
    reopen_rate: float | None
    csat: float | None
    rated: int
    resolution_hours: float | None


class CategoryMetrics(Metrics):
    name: str
    impact: int


class TrendPoint(Config):
    date: str
    total: int
    escalated: int
    resolved: int


class Distribution(Config):
    name: str
    value: int


class Insight(Config):
    title: str
    body: str


class OverviewOut(Config):
    oldest_open: list[TicketOut]
    kpis: Metrics
    categories: list[CategoryMetrics]
    weekly: list[TrendPoint]
    monthly: list[TrendPoint]
    priorities: list[Distribution]
    statuses: list[Distribution]
    clients: list[Distribution]
    outcomes: list[Distribution]
    ageing: list[Distribution]
    insights: list[Insight]
    baseline: Metrics
    range: list[str | None]


class EscalationPage(Config):
    items: list[TicketOut]
    total: int
    counts: dict[str, int]
