"""Read-only report calculation for completed general learning tests."""

from collections import defaultdict

from app.repositories.learning_repository import (
    LearningSessionAttemptDetails,
    get_learning_session,
    get_learning_session_attempt_details,
    get_learning_subtype_taxonomy,
)
from app.schemas.learning import (
    LearningTestReportResponse,
    LearningTestSubtypePerformanceResponse,
    TrapCountResponse,
)
from app.services.learning_test_service import (
    LEARNING_TEST_DB_MODE_TO_API_MODE,
    LEARNING_TEST_ITEM_LIMIT,
)


def get_learning_test_report(
    learning_session_id: str,
    learner_id: str,
) -> LearningTestReportResponse:
    """Build a read-only report for one completed general learning test."""
    session = get_learning_session(learning_session_id)

    if session is None:
        raise ValueError("Learning test session not found.")

    if session["learner_id"] != learner_id:
        raise ValueError("Learning test session not found.")

    api_mode = LEARNING_TEST_DB_MODE_TO_API_MODE.get(session["mode"])
    if api_mode is None:
        raise ValueError("Learning session is not a general learning test session.")

    if session["status"] != "completed":
        raise ValueError("Learning test session is not completed.")

    attempts = get_learning_session_attempt_details(learning_session_id)
    if not attempts:
        raise RuntimeError("Completed learning test session has no attempts.")
    if len(attempts) != LEARNING_TEST_ITEM_LIMIT:
        raise RuntimeError(
            "Completed learning test session must have exactly "
            f"{LEARNING_TEST_ITEM_LIMIT} attempts."
        )

    attempts_by_subtype: dict[str, list[LearningSessionAttemptDetails]] = defaultdict(list)
    correct_count = 0
    trap_count_by_id: dict[str, int] = {}

    for attempt in attempts:
        if attempt["context"] != session["mode"]:
            raise RuntimeError("Learning test attempt context does not match session mode.")

        subtype_id = attempt["subtype_id"]
        if subtype_id is None:
            raise RuntimeError("Learning test attempt is missing subtype data.")

        attempts_by_subtype[subtype_id].append(attempt)

        if attempt["is_correct"]:
            correct_count += 1
            continue

        trap_id = attempt["trap_id"]
        if trap_id is not None:
            trap_count_by_id[trap_id] = trap_count_by_id.get(trap_id, 0) + 1

    performances = _build_subtype_performances(attempts_by_subtype)
    ordered_low_to_high = sorted(
        performances,
        key=lambda performance: (
            performance.accuracy,
            -performance.attempted_count,
            performance.subtype_id,
        ),
    )
    review_subtypes = ordered_low_to_high[:3]
    review_subtype_ids = {performance.subtype_id for performance in review_subtypes}
    strengths = [
        performance
        for performance in sorted(
            performances,
            key=lambda performance: (
                -performance.accuracy,
                -performance.attempted_count,
                performance.subtype_id,
            ),
        )
        if performance.subtype_id not in review_subtype_ids
    ][:3]

    total_questions = len(attempts)
    trap_counts = [
        TrapCountResponse(trap_id=trap_id, count=count)
        for trap_id, count in sorted(
            trap_count_by_id.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]

    return LearningTestReportResponse(
        learning_session_id=learning_session_id,
        mode=api_mode,
        status="completed",
        total_questions=total_questions,
        correct_count=correct_count,
        accuracy=round(correct_count / total_questions * 100, 2),
        strengths=strengths,
        review_subtypes=review_subtypes,
        trap_counts=trap_counts,
        started_at=session["started_at"],
        completed_at=session["completed_at"],
    )


def _build_subtype_performances(
    attempts_by_subtype: dict[str, list[LearningSessionAttemptDetails]],
) -> list[LearningTestSubtypePerformanceResponse]:
    """Calculate taxonomy-backed performance for every attempted subtype."""
    performances: list[LearningTestSubtypePerformanceResponse] = []

    for subtype_id, attempts in attempts_by_subtype.items():
        taxonomy = get_learning_subtype_taxonomy(subtype_id)
        if taxonomy is None:
            raise RuntimeError("Learning test subtype taxonomy was not found.")
        if None in (
            taxonomy["subtype_name"],
            taxonomy["type_id"],
            taxonomy["type_name"],
        ):
            raise RuntimeError("Learning test subtype taxonomy is incomplete.")

        attempted_count = len(attempts)
        subtype_correct_count = sum(attempt["is_correct"] is True for attempt in attempts)
        performances.append(
            LearningTestSubtypePerformanceResponse(
                subtype_id=subtype_id,
                subtype_name=taxonomy["subtype_name"],
                type_id=taxonomy["type_id"],
                type_name=taxonomy["type_name"],
                attempted_count=attempted_count,
                correct_count=subtype_correct_count,
                accuracy=round(subtype_correct_count / attempted_count * 100, 2),
            )
        )

    return performances
