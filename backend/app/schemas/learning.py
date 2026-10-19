"""Request and response schemas for weak-subtype learning endpoints."""

from typing import Literal

from pydantic import BaseModel

from app.schemas.diagnostic import ChoiceLabel

LearningTestMode = Literal["general", "vocabulary", "grammar"]


class PracticeChoiceResponse(BaseModel):
    label: str
    text: str


class WeakLearningItemResponse(BaseModel):
    id: str
    subtype_id: str
    part: str
    difficulty: str | None
    stem: str
    translation: str | None
    choices: list[PracticeChoiceResponse]


class WeakLearningSubmitRequest(BaseModel):
    learning_session_id: str
    question_id: str
    selected_choice: ChoiceLabel


class WeakLearningSubmitResponse(BaseModel):
    question_id: str
    attempt_id: int | None = None
    subtype_id: str
    selected_choice: ChoiceLabel
    correct_choice: ChoiceLabel
    is_correct: bool
    trap_id: str | None = None
    correct_streak: int = 0
    is_completed: bool = False


class WeakLearningStartRequest(BaseModel):
    subtype_id: str


class WeakLearningStartResponse(BaseModel):
    learning_session_id: str
    subtype_id: str
    status: Literal["in_progress"]


class LearningTestStartRequest(BaseModel):
    mode: LearningTestMode


class LearningTestStartResponse(BaseModel):
    learning_session_id: str
    mode: LearningTestMode
    status: Literal["in_progress"]


class LearningTestItemResponse(BaseModel):
    id: str
    subtype_id: str
    part: str
    difficulty: str | None
    stem: str
    translation: str | None
    choices: list[PracticeChoiceResponse]


class LearningTestItemsResponse(BaseModel):
    learning_session_id: str
    mode: LearningTestMode
    items: list[LearningTestItemResponse]
    count: int


class LearningTestAnswerSubmission(BaseModel):
    question_id: str
    selected_choice: ChoiceLabel


class LearningTestSubmitRequest(BaseModel):
    learning_session_id: str
    answers: list[LearningTestAnswerSubmission]


class LearningTestItemGradingResult(BaseModel):
    question_id: str
    attempt_id: int | None = None
    subtype_id: str
    selected_choice: ChoiceLabel
    correct_choice: ChoiceLabel
    is_correct: bool
    trap_id: str | None = None


class LearningTestSubmitResponse(BaseModel):
    learning_session_id: str
    mode: LearningTestMode
    total_questions: int
    correct_count: int
    accuracy: float
    results: list[LearningTestItemGradingResult]
    status: Literal["completed"]


class TrapCountResponse(BaseModel):
    trap_id: str
    count: int


class LearningTestSubtypePerformanceResponse(BaseModel):
    subtype_id: str
    subtype_name: str
    type_id: str
    type_name: str
    attempted_count: int
    correct_count: int
    accuracy: float


class LearningTestReportResponse(BaseModel):
    learning_session_id: str
    mode: LearningTestMode
    status: Literal["completed"]
    total_questions: int
    correct_count: int
    accuracy: float
    strengths: list[LearningTestSubtypePerformanceResponse]
    review_subtypes: list[LearningTestSubtypePerformanceResponse]
    trap_counts: list[TrapCountResponse]
    started_at: str
    completed_at: str | None


class WeakLearningReportResponse(BaseModel):
    learning_session_id: str
    subtype_id: str
    subtype_name: str
    type_id: str
    type_name: str
    status: str
    total_questions: int
    correct_count: int
    accuracy: float
    final_correct_streak: int
    trap_counts: list[TrapCountResponse]
    started_at: str
    completed_at: str | None


class WrongReviewStartResponse(BaseModel):
    session_id: str
    total_count: int


class WrongReviewItemsResponse(BaseModel):
    session_id: str
    total_count: int
    items: list[LearningTestItemResponse]


class WrongReviewAnswerSubmission(BaseModel):
    question_id: str
    selected_choice: ChoiceLabel


class WrongReviewSubmitRequest(BaseModel):
    session_id: str
    answers: list[WrongReviewAnswerSubmission]


class WrongReviewResultResponse(BaseModel):
    question_id: str
    attempt_id: int | None = None
    subtype_id: str
    selected_choice: ChoiceLabel
    correct_choice: ChoiceLabel
    is_correct: bool
    trap_id: str | None = None


class WrongReviewSubmitResponse(BaseModel):
    session_id: str
    total_count: int
    correct_count: int
    accuracy: float
    results: list[WrongReviewResultResponse]
    status: Literal["completed"]


class WrongReviewReportResponse(BaseModel):
    session_id: str
    total_count: int
    correct_count: int
    accuracy: float
    remaining_wrong_count: int
    completed_at: str | None


class LearningRecommendationTrapResponse(BaseModel):
    trap_id: str
    name: str
    description: str | None
    wrong_count: int
    last_seen_at: str


class LearningRecommendationItemResponse(BaseModel):
    subtype_id: str
    subtype_name: str
    type_id: str
    type_name: str
    priority_score: float
    total_attempts: int
    correct_count: int
    wrong_count: int
    accuracy: float
    last_attempted_at: str
    last_is_correct: bool
    recent_wrong_count: int
    top_traps: list[LearningRecommendationTrapResponse]
    reason: list[str]


class LearningStrengthItemResponse(BaseModel):
    subtype_id: str
    subtype_name: str
    type_id: str
    type_name: str
    total_attempts: int
    correct_count: int
    wrong_count: int
    accuracy: float
    last_attempted_at: str
    last_is_correct: bool
    reason: list[str]


class LearningRecommendationSummaryResponse(BaseModel):
    total_attempts: int
    analyzed_subtypes: int


class LearningRecommendationsResponse(BaseModel):
    recommendations: list[LearningRecommendationItemResponse]
    strengths: list[LearningStrengthItemResponse]
    summary: LearningRecommendationSummaryResponse
