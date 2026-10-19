"""Request and response schemas for free diagnostic endpoints."""

from typing import Literal

from pydantic import BaseModel

ChoiceLabel = Literal["A", "B", "C", "D"]


class DiagnosticChoiceResponse(BaseModel):
    label: str
    text: str


class DiagnosticItemResponse(BaseModel):
    id: str
    subtype_id: str
    part: str
    difficulty: str | None
    stem: str
    translation: str | None
    choices: list[DiagnosticChoiceResponse]


class DiagnosticItemsResponse(BaseModel):
    items: list[DiagnosticItemResponse]
    count: int


class DiagnosticAnswerSubmission(BaseModel):
    question_id: str
    selected_choice: ChoiceLabel


class DiagnosticSubmitRequest(BaseModel):
    answers: list[DiagnosticAnswerSubmission]


class DiagnosticItemGradingResult(BaseModel):
    question_id: str
    attempt_id: int | None = None
    subtype_id: str
    selected_choice: ChoiceLabel
    correct_choice: ChoiceLabel
    is_correct: bool
    trap_id: str | None = None


class DiagnosticGradingResponse(BaseModel):
    total_count: int
    correct_count: int
    accuracy: float
    results: list[DiagnosticItemGradingResult]


class DiagnosticSubmitResponse(DiagnosticGradingResponse):
    session_id: str


class DiagnosticSubtypePerformanceResponse(BaseModel):
    subtype_id: str
    subtype_name: str
    type_id: str
    type_name: str
    attempted_count: int
    correct_count: int
    accuracy: float


class DiagnosticReportResponse(BaseModel):
    diagnostic_session_id: str
    total_count: int
    correct_count: int
    accuracy: float
    estimated_score: int | None
    strengths: list[DiagnosticSubtypePerformanceResponse]
    weaknesses: list[DiagnosticSubtypePerformanceResponse]
    recommended_learning_type: DiagnosticSubtypePerformanceResponse | None
