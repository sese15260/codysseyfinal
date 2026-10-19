"""Response schemas for authenticated vocabulary endpoints."""

from pydantic import BaseModel, Field


class TodayWordResponse(BaseModel):
    id: str
    word: str
    meaning: str
    example: str | None
    difficulty: str | None
    is_saved: bool
    is_memorized: bool


class TodayWordsResponse(BaseModel):
    date: str
    total_count: int
    words: list[TodayWordResponse]


class WordSavedStatusRequest(BaseModel):
    is_saved: bool


class WordMemorizedStatusRequest(BaseModel):
    is_memorized: bool


class WordStateResponse(BaseModel):
    word_id: str
    is_saved: bool
    is_memorized: bool
    saved_at: str | None
    memorized_at: str | None


class SavedWordResponse(BaseModel):
    id: str
    word: str
    meaning: str
    example: str | None
    difficulty: str | None
    is_saved: bool
    is_memorized: bool
    saved_at: str | None
    memorized_at: str | None


class SavedWordsResponse(BaseModel):
    total_count: int
    words: list[SavedWordResponse]


class VocabularyQuizStartResponse(BaseModel):
    session_id: str
    total_count: int


class VocabularyQuizItemResponse(BaseModel):
    word_id: str
    word: str
    choices: list[str]


class VocabularyQuizItemsResponse(BaseModel):
    session_id: str
    total_count: int
    items: list[VocabularyQuizItemResponse]


class VocabularyQuizAnswerSubmission(BaseModel):
    word_id: str
    selected_meaning: str = Field(min_length=1)


class VocabularyQuizSubmitRequest(BaseModel):
    session_id: str
    answers: list[VocabularyQuizAnswerSubmission]


class VocabularyQuizResultResponse(BaseModel):
    word_id: str
    word: str
    selected_meaning: str
    correct_meaning: str
    is_correct: bool


class VocabularyQuizSubmitResponse(BaseModel):
    session_id: str
    total_count: int
    correct_count: int
    accuracy: float
    results: list[VocabularyQuizResultResponse]
    status: str = "completed"
