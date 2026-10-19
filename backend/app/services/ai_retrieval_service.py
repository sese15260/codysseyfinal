"""Exact relational retrieval for a question-attempt explanation context."""

from typing import Any

from app.repositories.ai_explanation_repository import (
    OwnedQuestionAttempt,
    get_question_with_choices,
    get_subtype_with_knowledge,
    get_trap,
)


class ExplanationRetrievalError(RuntimeError):
    """Raised when data required to ground an explanation is inconsistent."""


def retrieve_explanation_context(attempt: OwnedQuestionAttempt) -> dict[str, Any]:
    """Build the exact taxonomy context for a persisted learner attempt."""
    question = get_question_with_choices(attempt["question_id"])
    if question is None:
        raise ExplanationRetrievalError("Question for attempt is missing.")

    subtype_id = question.get("subtype_id")
    if not subtype_id or attempt.get("subtype_id") != subtype_id:
        raise ExplanationRetrievalError("Attempt subtype data is inconsistent.")

    choices = sorted(
        question.get("question_choices") or [],
        key=lambda choice: choice["choice_label"],
    )
    selected_choice = next(
        (choice for choice in choices if choice.get("choice_label") == attempt["selected_choice"]),
        None,
    )
    correct_choices = [choice for choice in choices if choice.get("is_correct")]
    if selected_choice is None or len(correct_choices) != 1:
        raise ExplanationRetrievalError("Question choice data is incomplete.")

    subtype = get_subtype_with_knowledge(subtype_id)
    if subtype is None:
        raise ExplanationRetrievalError("Subtype for attempt is missing.")
    parent_type = subtype.get("types") or {}
    specs = subtype.get("subtype_specs")
    if isinstance(specs, list):
        specs = specs[0] if specs else None
    if not parent_type or not specs:
        raise ExplanationRetrievalError("Subtype knowledge data is incomplete.")

    trap: dict[str, Any] | None = None
    if attempt["trap_id"] is not None:
        trap = get_trap(attempt["trap_id"])
        if trap is None:
            raise ExplanationRetrievalError("Trap data for attempt is missing.")

    return {
        "question": {
            "id": question["id"],
            "stem": question["stem"],
            "translation": question.get("translation"),
            "part": question.get("part"),
            "difficulty": question.get("difficulty"),
            "choices": [
                {
                    "label": choice["choice_label"],
                    "text": choice["choice_text"],
                }
                for choice in choices
            ],
        },
        "attempt": {
            "selected_choice": attempt["selected_choice"],
            "selected_choice_text": selected_choice["choice_text"],
            "correct_choice": correct_choices[0]["choice_label"],
            "correct_choice_text": correct_choices[0]["choice_text"],
            "is_correct": attempt["is_correct"],
        },
        "subtype": {"id": subtype["id"], "name": subtype["name"]},
        "type": {"id": parent_type.get("id"), "name": parent_type.get("name")},
        "subtype_specs": {
            "answer_rule": specs.get("answer_rule"),
            "cues": specs.get("cues"),
            "judgment": specs.get("judgment"),
            "scope": specs.get("scope"),
            "option_pattern": specs.get("option_pattern"),
            "distractors": specs.get("distractors"),
            "vocab": specs.get("vocab"),
            "example_item": specs.get("example_item"),
            "notes": specs.get("notes"),
        },
        "trap": (
            None
            if trap is None
            else {
                "code": trap["id"],
                "name": trap["name"],
                "description": trap.get("description"),
            }
        ),
    }
