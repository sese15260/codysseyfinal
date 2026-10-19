"""Recommendation logic for weak-subtype practice."""

import random
from typing import TypedDict

from app.repositories.learning_repository import (
    complete_learning_session,
    create_learning_attempt,
    create_learning_session,
    get_learning_session,
    get_learning_session_attempts,
)
from app.repositories.question_repository import (
    PracticeQuestion,
    get_practice_question_grading_data,
    get_practice_questions_by_subtype,
    subtype_exists,
)
from app.schemas.learning import (
    WeakLearningSubmitRequest,
    WeakLearningSubmitResponse,
)


class WeakLearningProgress(TypedDict):
    learning_session_id: str
    correct_streak: int
    is_completed: bool


def get_weak_learning_item(subtype_id: str) -> PracticeQuestion | None:
    """Return one random public practice question for the requested subtype."""
    questions = get_practice_questions_by_subtype(subtype_id)

    if not questions:
        return None

    return random.choice(questions)


def start_weak_learning_session(
    subtype_id: str,
    learner_id: str,
) -> str:
    """Start an in-progress weak-subtype learning session."""
    if not subtype_exists(subtype_id):
        raise ValueError(f"Unknown subtype: {subtype_id}")

    if not get_practice_questions_by_subtype(subtype_id):
        raise ValueError(f"No practice questions found for subtype: {subtype_id}")

    return create_learning_session(
        learner_id=learner_id,
        mode="weak_learning",
        subtype_id=subtype_id,
        status="in_progress",
    )


def grade_weak_learning_answer(
    submission: WeakLearningSubmitRequest,
) -> WeakLearningSubmitResponse:
    """Grade one submitted public practice answer without persisting it."""
    grading_data = get_practice_question_grading_data(submission.question_id)

    if not grading_data["found"]:
        raise ValueError(
            f"Submitted question is missing or is not a practice question: {submission.question_id}"
        )

    subtype_id = grading_data["subtype_id"]
    correct_choice = grading_data["correct_choice_label"]

    if subtype_id is None or correct_choice is None:
        raise RuntimeError(
            f"Practice grading data is incomplete for question: {submission.question_id}"
        )

    is_correct = submission.selected_choice == correct_choice
    trap_id = None

    if not is_correct:
        trap_by_choice = {
            choice["choice_label"]: choice["trap_id"]
            for choice in grading_data["incorrect_choice_traps"]
        }
        trap_id = trap_by_choice.get(submission.selected_choice)

        if trap_id is None:
            raise RuntimeError(
                "Practice grading data is missing trap information for the "
                f"submitted choice: {submission.question_id}"
            )

    return WeakLearningSubmitResponse(
        question_id=submission.question_id,
        subtype_id=subtype_id,
        selected_choice=submission.selected_choice,
        correct_choice=correct_choice,
        is_correct=is_correct,
        trap_id=trap_id,
    )


def get_weak_learning_progress(
    learning_session_id: str,
) -> WeakLearningProgress:
    """Calculate the current consecutive-correct streak for one session."""
    attempts = get_learning_session_attempts(learning_session_id)
    correct_streak = 0

    for attempt in attempts:
        if not attempt["is_correct"]:
            break

        correct_streak += 1

    return {
        "learning_session_id": learning_session_id,
        "correct_streak": correct_streak,
        "is_completed": correct_streak >= 2,
    }


def submit_weak_learning_answer(
    submission: WeakLearningSubmitRequest,
    learner_id: str,
) -> WeakLearningSubmitResponse:
    """Validate a weak-learning session, grade an answer, and store its attempt."""
    session = get_learning_session(submission.learning_session_id)

    if session is None:
        raise ValueError("Learning session not found.")

    if session["learner_id"] != learner_id:
        raise ValueError("Learning session not found.")

    if session["mode"] != "weak_learning":
        raise ValueError("Learning session is not a weak-learning session.")

    if session["status"] != "in_progress":
        raise ValueError("Learning session is not in progress.")

    session_subtype_id = session["subtype_id"]

    if session_subtype_id is None:
        raise RuntimeError("Learning session is missing subtype data.")

    result = grade_weak_learning_answer(submission)

    if result.subtype_id != session_subtype_id:
        raise ValueError("Submitted question does not match the learning session subtype.")

    result.attempt_id = create_learning_attempt(
        learner_id=learner_id,
        learning_session_id=submission.learning_session_id,
        result=result,
    )

    progress = get_weak_learning_progress(submission.learning_session_id)

    if progress["is_completed"]:
        complete_learning_session(submission.learning_session_id)

    result.correct_streak = progress["correct_streak"]
    result.is_completed = progress["is_completed"]

    return result
