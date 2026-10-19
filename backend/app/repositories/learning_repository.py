"""Persistence queries for weak-subtype learning sessions and attempts."""

from datetime import datetime, timezone
from typing import TypedDict

from app.db.supabase import supabase
from app.schemas.learning import (
    LearningTestItemGradingResult,
    WeakLearningSubmitResponse,
)


class LearningSession(TypedDict):
    id: str
    learner_id: str | None
    mode: str
    subtype_id: str | None
    status: str
    started_at: str
    completed_at: str | None


class LearningSessionAttempt(TypedDict):
    question_id: str
    is_correct: bool
    answered_at: str


class LearningSessionAttemptDetails(TypedDict):
    question_id: str
    subtype_id: str | None
    selected_choice: str
    is_correct: bool
    trap_id: str | None
    context: str | None
    answered_at: str


class LearningSubtypeTaxonomy(TypedDict):
    subtype_id: str
    subtype_name: str | None
    type_id: str | None
    type_name: str | None


class LearningSessionQuestion(TypedDict):
    question_id: str
    position: int


class LearnerQuestionAttempt(TypedDict):
    question_id: str
    is_correct: bool
    answered_at: str
    id: int


def create_learning_session(
    *,
    subtype_id: str | None,
    learner_id: str | None = None,
    mode: str = "weak_learning",
    status: str = "in_progress",
) -> str:
    """Create a learning session and return its generated ID."""
    started_at = datetime.now(timezone.utc).isoformat()
    session = {
        "learner_id": learner_id,
        "mode": mode,
        "subtype_id": subtype_id,
        "status": status,
        "started_at": started_at,
    }

    if status == "completed":
        session["completed_at"] = started_at

    response = supabase.table("learning_sessions").insert(session).execute()

    if not response.data:
        raise RuntimeError("Learning session insert did not return an ID.")

    return response.data[0]["id"]


def create_learning_attempt(
    *,
    learning_session_id: str,
    result: WeakLearningSubmitResponse,
    learner_id: str | None = None,
) -> int:
    """Store one weak-learning attempt and return its generated ID."""
    response = (
        supabase.table("question_attempts")
        .insert(
            {
                "learner_id": learner_id,
                "diagnostic_session_id": None,
                "learning_session_id": learning_session_id,
                "question_id": result.question_id,
                "subtype_id": result.subtype_id,
                "selected_choice": result.selected_choice,
                "is_correct": result.is_correct,
                "trap_id": result.trap_id,
                "context": "weak_learning",
                "answered_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        .execute()
    )
    if not response.data:
        raise RuntimeError("Learning attempt insert did not return an ID.")

    inserted_attempt = response.data[0]
    attempt_id = inserted_attempt.get("id")
    if not isinstance(attempt_id, int) or inserted_attempt.get("question_id") != result.question_id:
        raise RuntimeError("Learning attempt insert returned incomplete data.")

    return attempt_id


def create_learning_test_attempts(
    *,
    learning_session_id: str,
    results: list[LearningTestItemGradingResult],
    context: str,
    learner_id: str | None = None,
) -> dict[str, int]:
    """Bulk insert attempts and return generated IDs keyed by question ID."""
    if not results:
        return {}

    answered_at = datetime.now(timezone.utc).isoformat()
    attempts = [
        {
            "learner_id": learner_id,
            "diagnostic_session_id": None,
            "learning_session_id": learning_session_id,
            "question_id": result.question_id,
            "subtype_id": result.subtype_id,
            "selected_choice": result.selected_choice,
            "is_correct": result.is_correct,
            "trap_id": result.trap_id,
            "context": context,
            "answered_at": answered_at,
        }
        for result in results
    ]

    response = supabase.table("question_attempts").insert(attempts).execute()
    return _attempt_ids_by_question_id(response.data, [result.question_id for result in results])


def _attempt_ids_by_question_id(
    inserted_rows: list[dict[str, object]],
    expected_question_ids: list[str],
) -> dict[str, int]:
    """Validate bulk insert output without relying on returned row order."""
    if len(expected_question_ids) != len(set(expected_question_ids)):
        raise RuntimeError("Learning attempt question IDs must be unique.")

    attempt_ids: dict[str, int] = {}
    for row in inserted_rows:
        question_id = row.get("question_id")
        attempt_id = row.get("id")
        if not isinstance(question_id, str) or not isinstance(attempt_id, int):
            raise RuntimeError("Learning attempt insert returned incomplete data.")
        if question_id in attempt_ids:
            raise RuntimeError("Learning attempt insert returned duplicate question IDs.")
        attempt_ids[question_id] = attempt_id

    if set(attempt_ids) != set(expected_question_ids):
        raise RuntimeError("Learning attempt insert did not return every question ID.")

    return attempt_ids


def get_learning_session(learning_session_id: str) -> LearningSession | None:
    """Return the data required to validate and report on a learning session."""
    response = (
        supabase.table("learning_sessions")
        .select("id, learner_id, mode, subtype_id, status, started_at, completed_at")
        .eq("id", learning_session_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0]


def get_learning_session_question_ids(
    learning_session_id: str,
) -> list[LearningSessionQuestion]:
    """Return one session's assigned question IDs in fixed position order."""
    response = (
        supabase.table("learning_session_questions")
        .select("question_id, position")
        .eq("learning_session_id", learning_session_id)
        .order("position")
        .execute()
    )

    return response.data


def create_learning_session_questions(
    learning_session_id: str,
    question_ids: list[str],
) -> None:
    """Persist a session's assigned questions in their supplied order."""
    if len(question_ids) != len(set(question_ids)):
        raise ValueError("Learning session question IDs must be unique.")

    if not question_ids:
        return

    assignments = [
        {
            "learning_session_id": learning_session_id,
            "question_id": question_id,
            "position": position,
        }
        for position, question_id in enumerate(question_ids, start=1)
    ]

    supabase.table("learning_session_questions").insert(assignments).execute()


def get_learning_session_attempts(
    learning_session_id: str,
) -> list[LearningSessionAttempt]:
    """Return one session's attempts with the newest answer first."""
    response = (
        supabase.table("question_attempts")
        .select("question_id, is_correct, answered_at")
        .eq("learning_session_id", learning_session_id)
        .order("answered_at", desc=True)
        .execute()
    )

    return response.data


def get_learning_session_attempt_details(
    learning_session_id: str,
) -> list[LearningSessionAttemptDetails]:
    """Return report fields for attempts in one learning session, newest first."""
    response = (
        supabase.table("question_attempts")
        .select(
            "question_id, subtype_id, selected_choice, is_correct, trap_id, context, answered_at"
        )
        .eq("learning_session_id", learning_session_id)
        .order("answered_at", desc=True)
        .execute()
    )

    return response.data


def get_learner_question_attempts(learner_id: str) -> list[LearnerQuestionAttempt]:
    """Return TOEIC attempts newest first for unresolved-wrong calculation."""
    response = (
        supabase.table("question_attempts")
        .select("id, question_id, is_correct, answered_at")
        .eq("learner_id", learner_id)
        .order("answered_at", desc=True)
        .order("id", desc=True)
        .execute()
    )
    return response.data


def get_learning_subtype_taxonomy(
    subtype_id: str,
) -> LearningSubtypeTaxonomy | None:
    """Return one subtype and its parent type display data."""
    response = (
        supabase.table("subtypes")
        .select("id, name, type_id, types(id, name)")
        .eq("id", subtype_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    subtype = response.data[0]
    question_type = subtype.get("types") or {}

    return {
        "subtype_id": subtype["id"],
        "subtype_name": subtype.get("name"),
        "type_id": subtype.get("type_id"),
        "type_name": question_type.get("name"),
    }


def complete_learning_session(learning_session_id: str) -> None:
    """Mark a learning session as completed at the current UTC time."""
    supabase.table("learning_sessions").update(
        {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", learning_session_id).execute()
