"""Session workflows for general learning tests."""

import random

from app.repositories.learning_repository import (
    LearningSessionQuestion,
    complete_learning_session,
    create_learning_session,
    create_learning_session_questions,
    create_learning_test_attempts,
    get_learning_session,
    get_learning_session_question_ids,
)
from app.repositories.question_repository import (
    get_practice_questions_by_area_codes,
    get_practice_questions_grading_data,
    get_public_questions_by_ids,
)
from app.schemas.learning import (
    LearningTestItemGradingResult,
    LearningTestItemResponse,
    LearningTestItemsResponse,
    LearningTestSubmitRequest,
    LearningTestSubmitResponse,
)

LEARNING_TEST_MODE_TO_DB_MODE = {
    "general": "daily_general",
    "vocabulary": "daily_vocabulary",
    "grammar": "daily_grammar",
}

LEARNING_TEST_DB_MODE_TO_API_MODE = {
    db_mode: api_mode for api_mode, db_mode in LEARNING_TEST_MODE_TO_DB_MODE.items()
}

LEARNING_TEST_MODE_TO_AREA_CODES = {
    "general": ["G", "V", "C"],
    "vocabulary": ["V"],
    "grammar": ["G"],
}

LEARNING_TEST_ITEM_LIMIT = 20


def start_learning_test_session(
    mode: str,
    learner_id: str,
) -> str:
    """Start an in-progress session for one authenticated learning-test user."""
    db_mode = LEARNING_TEST_MODE_TO_DB_MODE.get(mode)

    if db_mode is None:
        raise ValueError(f"Unsupported learning test mode: {mode}")

    return create_learning_session(
        learner_id=learner_id,
        mode=db_mode,
        subtype_id=None,
        status="in_progress",
    )


def get_learning_test_items(
    learning_session_id: str,
    learner_id: str,
) -> LearningTestItemsResponse:
    """Return one active test session's fixed public practice questions."""
    session = get_learning_session(learning_session_id)

    if session is None:
        raise ValueError("Learning test session not found.")

    if session["learner_id"] != learner_id:
        raise ValueError("Learning test session not found.")

    if session["status"] != "in_progress":
        raise ValueError("Learning test session is not in progress.")

    api_mode = LEARNING_TEST_DB_MODE_TO_API_MODE.get(session["mode"])
    if api_mode is None:
        raise ValueError("Learning session is not a general learning test session.")

    assignments = get_learning_session_question_ids(learning_session_id)
    if assignments:
        return _build_items_response(
            learning_session_id=learning_session_id,
            api_mode=api_mode,
            assignments=assignments,
        )

    candidates = get_practice_questions_by_area_codes(LEARNING_TEST_MODE_TO_AREA_CODES[api_mode])

    if len(candidates) < LEARNING_TEST_ITEM_LIMIT:
        raise RuntimeError(
            f"Not enough practice questions to create a learning test for mode: {api_mode}"
        )

    question_ids = [
        question["id"] for question in random.sample(candidates, k=LEARNING_TEST_ITEM_LIMIT)
    ]

    try:
        create_learning_session_questions(learning_session_id, question_ids)
    except Exception:
        concurrent_assignments = get_learning_session_question_ids(learning_session_id)
        if len(concurrent_assignments) == LEARNING_TEST_ITEM_LIMIT:
            return _build_items_response(
                learning_session_id=learning_session_id,
                api_mode=api_mode,
                assignments=concurrent_assignments,
            )
        raise

    return _build_items_response(
        learning_session_id=learning_session_id,
        api_mode=api_mode,
        assignments=get_learning_session_question_ids(learning_session_id),
    )


def submit_learning_test(
    submission: LearningTestSubmitRequest,
    learner_id: str,
) -> LearningTestSubmitResponse:
    """Grade, persist, and complete one fully assigned learning test session."""
    session = get_learning_session(submission.learning_session_id)

    if session is None:
        raise ValueError("Learning test session not found.")

    if session["learner_id"] != learner_id:
        raise ValueError("Learning test session not found.")

    if session["status"] != "in_progress":
        raise ValueError("Learning test session is not in progress.")

    api_mode = LEARNING_TEST_DB_MODE_TO_API_MODE.get(session["mode"])
    if api_mode is None:
        raise ValueError("Learning session is not a general learning test session.")

    answers = submission.answers
    if not answers:
        raise ValueError("Learning test answers must not be empty.")

    if len(answers) != LEARNING_TEST_ITEM_LIMIT:
        raise ValueError(f"Learning test requires exactly {LEARNING_TEST_ITEM_LIMIT} answers.")

    submitted_question_ids = [answer.question_id for answer in answers]
    if len(submitted_question_ids) != len(set(submitted_question_ids)):
        raise ValueError("Learning test answers contain duplicate question IDs.")

    assignments = get_learning_session_question_ids(submission.learning_session_id)
    assigned_question_ids = _get_assigned_question_ids(assignments)
    if set(submitted_question_ids) != set(assigned_question_ids):
        raise ValueError("Submitted questions do not match the session assignment.")

    grading_data = get_practice_questions_grading_data(submitted_question_ids)
    results: list[LearningTestItemGradingResult] = []

    for answer, question in zip(answers, grading_data, strict=True):
        if not question["found"]:
            raise ValueError("Submitted question is not a practice question.")

        subtype_id = question["subtype_id"]
        correct_choice = question["correct_choice_label"]
        if subtype_id is None or correct_choice is None:
            raise RuntimeError("Practice question grading data is incomplete.")

        is_correct = answer.selected_choice == correct_choice
        trap_id: str | None = None

        if not is_correct:
            trap_id = next(
                (
                    trap["trap_id"]
                    for trap in question["incorrect_choice_traps"]
                    if trap["choice_label"] == answer.selected_choice
                ),
                None,
            )
            if trap_id is None:
                raise RuntimeError("Practice question trap data is incomplete.")

        results.append(
            LearningTestItemGradingResult(
                question_id=answer.question_id,
                subtype_id=subtype_id,
                selected_choice=answer.selected_choice,
                correct_choice=correct_choice,
                is_correct=is_correct,
                trap_id=trap_id,
            )
        )

    correct_count = sum(result.is_correct for result in results)
    accuracy = round(correct_count / LEARNING_TEST_ITEM_LIMIT * 100, 2)

    attempt_ids_by_question_id = create_learning_test_attempts(
        learning_session_id=submission.learning_session_id,
        results=results,
        context=session["mode"],
        learner_id=learner_id,
    )
    for result in results:
        result.attempt_id = attempt_ids_by_question_id[result.question_id]
    complete_learning_session(submission.learning_session_id)

    return LearningTestSubmitResponse(
        learning_session_id=submission.learning_session_id,
        mode=api_mode,
        total_questions=LEARNING_TEST_ITEM_LIMIT,
        correct_count=correct_count,
        accuracy=accuracy,
        results=results,
        status="completed",
    )


def _build_items_response(
    *,
    learning_session_id: str,
    api_mode: str,
    assignments: list[LearningSessionQuestion],
) -> LearningTestItemsResponse:
    """Build a public response from complete, position-ordered assignments."""
    question_ids = _get_assigned_question_ids(assignments)
    items = get_public_questions_by_ids(question_ids)

    if len(items) != LEARNING_TEST_ITEM_LIMIT:
        raise RuntimeError("Learning test session has missing assigned questions.")

    return LearningTestItemsResponse(
        learning_session_id=learning_session_id,
        mode=api_mode,
        items=[LearningTestItemResponse(**item) for item in items],
        count=len(items),
    )


def _get_assigned_question_ids(
    assignments: list[LearningSessionQuestion],
) -> list[str]:
    """Validate a complete fixed assignment and return it in position order."""
    if len(assignments) != LEARNING_TEST_ITEM_LIMIT:
        raise RuntimeError("Learning test session has a partial question assignment.")

    positions = [assignment["position"] for assignment in assignments]
    if positions != list(range(1, LEARNING_TEST_ITEM_LIMIT + 1)):
        raise RuntimeError("Learning test session question positions are invalid.")

    return [assignment["question_id"] for assignment in assignments]
