"""Application logic for serving free diagnostic questions."""

import random

from app.repositories.diagnostic_repository import (
    create_diagnostic_session,
    create_question_attempts,
)
from app.repositories.question_repository import (
    DiagnosticQuestion,
    get_diagnostic_question_grading_data,
    get_diagnostic_questions,
)
from app.schemas.diagnostic import (
    DiagnosticGradingResponse,
    DiagnosticItemGradingResult,
    DiagnosticSubmitRequest,
    DiagnosticSubmitResponse,
)

DEFAULT_DIAGNOSTIC_ITEM_LIMIT = 20


def get_diagnostic_items(
    limit: int = DEFAULT_DIAGNOSTIC_ITEM_LIMIT,
) -> list[DiagnosticQuestion]:
    """Return up to ``limit`` diagnostic questions in random order.

    The repository supplies only public question data, so this service does not
    add grading fields such as correct answers or traps to the returned items.
    """
    if limit <= 0:
        return []

    questions = get_diagnostic_questions()

    if not questions:
        return []

    return random.sample(questions, k=min(limit, len(questions)))


def grade_diagnostic_answers(
    submission: DiagnosticSubmitRequest,
) -> DiagnosticGradingResponse:
    """Grade submitted diagnostic answers without persisting session data."""
    answers = submission.answers

    if not answers:
        raise ValueError("At least one diagnostic answer is required.")

    question_ids = [answer.question_id for answer in answers]

    if len(set(question_ids)) != len(question_ids):
        raise ValueError("Duplicate diagnostic question IDs are not allowed.")

    grading_data = get_diagnostic_question_grading_data(question_ids)

    if len(grading_data) != len(answers):
        raise RuntimeError("Diagnostic grading data does not match submitted answers.")

    results: list[DiagnosticItemGradingResult] = []
    correct_count = 0

    for answer, question_data in zip(answers, grading_data):
        question_id = answer.question_id

        if not question_data["found"]:
            raise ValueError(
                f"Submitted question is missing or is not a diagnostic question: {question_id}"
            )

        subtype_id = question_data["subtype_id"]
        correct_choice = question_data["correct_choice_label"]

        if subtype_id is None or correct_choice is None:
            raise RuntimeError(f"Diagnostic grading data is incomplete for question: {question_id}")

        is_correct = answer.selected_choice == correct_choice
        trap_id = None

        if not is_correct:
            incorrect_choice_traps = {
                choice["choice_label"]: choice["trap_id"]
                for choice in question_data["incorrect_choice_traps"]
            }

            if answer.selected_choice not in incorrect_choice_traps:
                raise RuntimeError(
                    "Diagnostic grading data is missing the submitted choice for "
                    f"question: {question_id}"
                )

            trap_id = incorrect_choice_traps[answer.selected_choice]
        else:
            correct_count += 1

        results.append(
            DiagnosticItemGradingResult(
                question_id=question_id,
                subtype_id=subtype_id,
                selected_choice=answer.selected_choice,
                correct_choice=correct_choice,
                is_correct=is_correct,
                trap_id=trap_id,
            )
        )

    total_count = len(results)
    accuracy = (correct_count / total_count * 100) if total_count else 0.0

    return DiagnosticGradingResponse(
        total_count=total_count,
        correct_count=correct_count,
        accuracy=accuracy,
        results=results,
    )


def submit_diagnostic(
    submission: DiagnosticSubmitRequest,
    learner_id: str | None = None,
) -> DiagnosticSubmitResponse:
    """Grade a diagnostic submission and persist its session and attempts."""
    grading_result = grade_diagnostic_answers(submission)

    diagnostic_session_id = create_diagnostic_session(
        learner_id=learner_id,
        total_questions=grading_result.total_count,
        correct_count=grading_result.correct_count,
        accuracy=grading_result.accuracy,
        estimated_score=None,
    )

    attempt_ids_by_question_id = create_question_attempts(
        learner_id=learner_id,
        diagnostic_session_id=diagnostic_session_id,
        results=grading_result.results,
    )

    for result in grading_result.results:
        result.attempt_id = attempt_ids_by_question_id[result.question_id]

    return DiagnosticSubmitResponse(
        session_id=diagnostic_session_id,
        total_count=grading_result.total_count,
        correct_count=grading_result.correct_count,
        accuracy=grading_result.accuracy,
        results=grading_result.results,
    )
