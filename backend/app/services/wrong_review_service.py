"""Application rules for learner-owned TOEIC wrong-answer review sessions."""

from app.repositories.learning_repository import (
    complete_learning_session,
    create_learning_session,
    create_learning_session_questions,
    create_learning_test_attempts,
    get_learner_question_attempts,
    get_learning_session,
    get_learning_session_attempt_details,
    get_learning_session_question_ids,
)
from app.repositories.question_repository import (
    get_public_toeic_questions_by_ids,
    get_toeic_questions_grading_data,
)
from app.schemas.learning import (
    LearningTestItemGradingResult,
    LearningTestItemResponse,
    WrongReviewItemsResponse,
    WrongReviewReportResponse,
    WrongReviewResultResponse,
    WrongReviewStartResponse,
    WrongReviewSubmitRequest,
    WrongReviewSubmitResponse,
)

WRONG_REVIEW_MODE = "wrong_review"
WRONG_REVIEW_ITEM_LIMIT = 20


def get_unresolved_wrong_question_ids(learner_id: str) -> list[str]:
    """Return unique question IDs whose newest learner attempt is incorrect."""
    latest_attempt_by_question: dict[str, bool] = {}
    ordered_question_ids: list[str] = []
    for attempt in get_learner_question_attempts(learner_id):
        question_id = attempt["question_id"]
        if question_id in latest_attempt_by_question:
            continue
        latest_attempt_by_question[question_id] = attempt["is_correct"]
        if not attempt["is_correct"]:
            ordered_question_ids.append(question_id)
    return ordered_question_ids


def _get_owned_wrong_review_session(
    session_id: str,
    learner_id: str,
) -> dict[str, object]:
    """Return a wrong-review session only when owned by the caller."""
    session = get_learning_session(session_id)
    if session is None or session["learner_id"] != learner_id:
        raise ValueError("Wrong review session not found.")
    if session["mode"] != WRONG_REVIEW_MODE:
        raise ValueError("Learning session is not a wrong review session.")
    return session


def _assigned_question_ids(session_id: str) -> list[str]:
    """Validate one non-empty, consecutively positioned review assignment."""
    assignments = get_learning_session_question_ids(session_id)
    if not assignments:
        raise RuntimeError("Wrong review session has no assigned questions.")
    positions = [assignment["position"] for assignment in assignments]
    if positions != list(range(1, len(assignments) + 1)):
        raise RuntimeError("Wrong review session question positions are invalid.")
    return [assignment["question_id"] for assignment in assignments]


def start_wrong_review(learner_id: str) -> WrongReviewStartResponse:
    """Create a fixed session from up to 20 most recently unresolved questions."""
    question_ids = get_unresolved_wrong_question_ids(learner_id)[:WRONG_REVIEW_ITEM_LIMIT]
    if not question_ids:
        raise ValueError("No wrong questions available for review.")

    session_id = create_learning_session(
        learner_id=learner_id,
        mode=WRONG_REVIEW_MODE,
        subtype_id=None,
        status="in_progress",
    )
    create_learning_session_questions(session_id, question_ids)
    return WrongReviewStartResponse(session_id=session_id, total_count=len(question_ids))


def get_wrong_review_items(
    session_id: str,
    learner_id: str,
) -> WrongReviewItemsResponse:
    """Return fixed public TOEIC items for an owned review session."""
    _get_owned_wrong_review_session(session_id, learner_id)
    question_ids = _assigned_question_ids(session_id)
    questions = get_public_toeic_questions_by_ids(question_ids)
    if len(questions) != len(question_ids):
        raise RuntimeError("Wrong review session has missing assigned questions.")

    return WrongReviewItemsResponse(
        session_id=session_id,
        total_count=len(questions),
        items=[LearningTestItemResponse(**question) for question in questions],
    )


def submit_wrong_review(
    submission: WrongReviewSubmitRequest,
    learner_id: str,
) -> WrongReviewSubmitResponse:
    """Grade, store, and complete all answers for a fixed review session."""
    session = _get_owned_wrong_review_session(submission.session_id, learner_id)
    if session["status"] != "in_progress":
        raise ValueError("Wrong review session is not in progress.")

    assigned_question_ids = _assigned_question_ids(submission.session_id)
    answers = submission.answers
    submitted_question_ids = [answer.question_id for answer in answers]
    if not submitted_question_ids:
        raise ValueError("Wrong review answers must not be empty.")
    if len(submitted_question_ids) != len(set(submitted_question_ids)):
        raise ValueError("Wrong review answers contain duplicate question IDs.")
    if set(submitted_question_ids) != set(assigned_question_ids):
        raise ValueError("Submitted questions do not match the session assignment.")

    answers_by_question_id = {answer.question_id: answer for answer in answers}
    grading_data = get_toeic_questions_grading_data(assigned_question_ids)
    results: list[WrongReviewResultResponse] = []
    attempt_results: list[LearningTestItemGradingResult] = []
    for question in grading_data:
        if not question["found"]:
            raise RuntimeError("Wrong review grading question was not found.")
        subtype_id = question["subtype_id"]
        correct_choice = question["correct_choice_label"]
        if subtype_id is None or correct_choice is None:
            raise RuntimeError("Wrong review grading data is incomplete.")

        answer = answers_by_question_id[question["question_id"]]
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
                raise RuntimeError("Wrong review trap data is incomplete.")

        attempt_results.append(
            LearningTestItemGradingResult(
                question_id=question["question_id"],
                subtype_id=subtype_id,
                selected_choice=answer.selected_choice,
                correct_choice=correct_choice,
                is_correct=is_correct,
                trap_id=trap_id,
            )
        )
        results.append(
            WrongReviewResultResponse(
                question_id=question["question_id"],
                subtype_id=subtype_id,
                selected_choice=answer.selected_choice,
                correct_choice=correct_choice,
                is_correct=is_correct,
                trap_id=trap_id,
            )
        )

    attempt_ids_by_question_id = create_learning_test_attempts(
        learning_session_id=submission.session_id,
        results=attempt_results,
        context=WRONG_REVIEW_MODE,
        learner_id=learner_id,
    )
    for result in results:
        result.attempt_id = attempt_ids_by_question_id[result.question_id]
    complete_learning_session(submission.session_id)

    correct_count = sum(result.is_correct for result in results)
    total_count = len(results)
    return WrongReviewSubmitResponse(
        session_id=submission.session_id,
        total_count=total_count,
        correct_count=correct_count,
        accuracy=round(correct_count / total_count * 100, 2),
        results=results,
        status="completed",
    )


def get_wrong_review_report(
    session_id: str,
    learner_id: str,
) -> WrongReviewReportResponse:
    """Return summary totals and remaining unresolved wrong-question count."""
    session = _get_owned_wrong_review_session(session_id, learner_id)
    if session["status"] != "completed":
        raise ValueError("Wrong review session is not completed.")

    attempts = get_learning_session_attempt_details(session_id)
    if not attempts:
        raise RuntimeError("Completed wrong review session has no attempts.")
    if any(attempt["context"] != WRONG_REVIEW_MODE for attempt in attempts):
        raise RuntimeError("Wrong review attempt context does not match session mode.")

    total_count = len(attempts)
    correct_count = sum(attempt["is_correct"] is True for attempt in attempts)
    return WrongReviewReportResponse(
        session_id=session_id,
        total_count=total_count,
        correct_count=correct_count,
        accuracy=round(correct_count / total_count * 100, 2),
        remaining_wrong_count=len(get_unresolved_wrong_question_ids(learner_id)),
        completed_at=session["completed_at"],
    )
