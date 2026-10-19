"""Database queries for retrieval-grounded AI explanations and their cache."""

from typing import Any, TypedDict

from app.db.supabase import supabase


class OwnedQuestionAttempt(TypedDict):
    id: int
    learner_id: str
    question_id: str
    subtype_id: str | None
    selected_choice: str
    is_correct: bool
    trap_id: str | None


class CachedAIExplanation(TypedDict):
    attempt_id: int
    content: dict[str, Any]
    model: str


def get_owned_question_attempt(
    attempt_id: int,
    learner_id: str,
) -> OwnedQuestionAttempt | None:
    """Return one attempt only when it belongs to the requesting learner."""
    response = (
        supabase.table("question_attempts")
        .select("id, learner_id, question_id, subtype_id, selected_choice, is_correct, trap_id")
        .eq("id", attempt_id)
        .eq("learner_id", learner_id)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def get_question_with_choices(question_id: str) -> dict[str, Any] | None:
    """Return a question with all choice data needed for an internal explanation."""
    response = (
        supabase.table("questions")
        .select(
            "id, subtype_id, part, difficulty, stem, translation, "
            "question_choices(choice_label, choice_text, is_correct, trap_id)"
        )
        .eq("id", question_id)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def get_subtype_with_knowledge(subtype_id: str) -> dict[str, Any] | None:
    """Return a subtype, its parent type, and its stored instructor knowledge."""
    response = (
        supabase.table("subtypes")
        .select(
            "id, name, type_id, types(id, name), "
            "subtype_specs(answer_rule, cues, judgment, scope, option_pattern, "
            "distractors, vocab, example_item, notes)"
        )
        .eq("id", subtype_id)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def get_trap(trap_id: str) -> dict[str, Any] | None:
    """Return the instructor-defined trap details for an incorrect attempt."""
    response = (
        supabase.table("traps").select("id, name, description").eq("id", trap_id).limit(1).execute()
    )
    return response.data[0] if response.data else None


def get_cached_ai_explanation(attempt_id: int) -> CachedAIExplanation | None:
    """Return the cached explanation for an already-authorized attempt."""
    response = (
        supabase.table("ai_explanations")
        .select("attempt_id, content, model")
        .eq("attempt_id", attempt_id)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def create_ai_explanation(
    *,
    learner_id: str,
    attempt_id: int,
    content: dict[str, Any],
    model: str,
) -> None:
    """Persist a validated explanation; the unique constraint handles races."""
    supabase.table("ai_explanations").insert(
        {
            "learner_id": learner_id,
            "attempt_id": attempt_id,
            "content": content,
            "model": model,
        }
    ).execute()
