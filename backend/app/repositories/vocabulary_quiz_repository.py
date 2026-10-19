"""Persistence operations for fixed, learner-owned vocabulary quizzes."""

from datetime import datetime, timezone
from typing import TypedDict

from app.db.supabase import supabase


class VocabularyQuizSession(TypedDict):
    id: str
    learner_id: str
    status: str
    started_at: str
    completed_at: str | None


class VocabularyQuizItem(TypedDict):
    word_id: str
    position: int
    correct_meaning: str
    choices: list[str]
    vocabulary_words: dict[str, str] | None


def create_vocabulary_quiz_session(learner_id: str) -> str:
    """Create an in-progress vocabulary quiz session and return its ID."""
    response = (
        supabase.table("vocabulary_quiz_sessions")
        .insert(
            {
                "learner_id": learner_id,
                "status": "in_progress",
                "started_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .execute()
    )
    if not response.data:
        raise RuntimeError("Vocabulary quiz session insert did not return an ID.")
    return response.data[0]["id"]


def create_vocabulary_quiz_items(
    session_id: str,
    items: list[dict[str, object]],
) -> None:
    """Bulk insert fixed vocabulary quiz items for a newly created session."""
    if not items:
        return
    supabase.table("vocabulary_quiz_items").insert(items).execute()


def get_vocabulary_quiz_session(session_id: str) -> VocabularyQuizSession | None:
    """Return one vocabulary quiz session for ownership and status validation."""
    response = (
        supabase.table("vocabulary_quiz_sessions")
        .select("id, learner_id, status, started_at, completed_at")
        .eq("id", session_id)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def get_vocabulary_quiz_items(session_id: str) -> list[VocabularyQuizItem]:
    """Return stored item data, including correct meaning for internal grading."""
    response = (
        supabase.table("vocabulary_quiz_items")
        .select("word_id, position, correct_meaning, choices, vocabulary_words(word)")
        .eq("session_id", session_id)
        .order("position")
        .execute()
    )
    return response.data


def create_vocabulary_quiz_attempts(
    session_id: str,
    attempts: list[dict[str, object]],
) -> None:
    """Persist all graded answers for one vocabulary quiz submission."""
    if not attempts:
        return
    supabase.table("vocabulary_quiz_attempts").insert(attempts).execute()


def complete_vocabulary_quiz_session(session_id: str) -> None:
    """Mark one vocabulary quiz session completed after attempt storage succeeds."""
    (
        supabase.table("vocabulary_quiz_sessions")
        .update(
            {
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .eq("id", session_id)
        .execute()
    )
