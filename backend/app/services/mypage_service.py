"""Report-history composition for one authenticated learner."""

from collections import defaultdict

from app.repositories.learner_repository import Learner, update_learner_profile
from app.repositories.mypage_repository import (
    get_completed_diagnostic_sessions,
    get_completed_learning_sessions,
    get_diagnostic_attempt_results,
    get_learning_attempt_results,
)
from app.schemas.mypage import (
    MyPageReportItemResponse,
    MyPageReportsResponse,
    ProfileUpdateRequest,
)

LEARNING_MODE_METADATA = {
    "weak_learning": ("weak_learning", "weak_learning"),
    "daily_general": ("learning_test", "general"),
    "daily_vocabulary": ("learning_test", "vocabulary"),
    "daily_grammar": ("learning_test", "grammar"),
}


def _attempt_counts_by_session(
    attempts: list[dict[str, object]],
    session_key: str,
) -> dict[str, tuple[int, int]]:
    """Return total and correct attempt counts, grouped by a session FK column."""
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for attempt in attempts:
        session_id = attempt.get(session_key)
        if not isinstance(session_id, str):
            continue

        counts[session_id][0] += 1
        if attempt.get("is_correct") is True:
            counts[session_id][1] += 1

    return {
        session_id: (total_count, correct_count)
        for session_id, (total_count, correct_count) in counts.items()
    }


def _accuracy(correct_count: int, total_count: int) -> float:
    """Calculate the same two-decimal accuracy used by existing reports."""
    if total_count == 0:
        return 0.0
    return round(correct_count / total_count * 100, 2)


def get_my_report_history(learner_id: str) -> MyPageReportsResponse:
    """Build a merged, newest-first history of a learner's actual reports."""
    diagnostic_sessions = get_completed_diagnostic_sessions(learner_id)
    learning_sessions = get_completed_learning_sessions(learner_id)

    diagnostic_counts = _attempt_counts_by_session(
        get_diagnostic_attempt_results([session["id"] for session in diagnostic_sessions]),
        "diagnostic_session_id",
    )
    learning_counts = _attempt_counts_by_session(
        get_learning_attempt_results([session["id"] for session in learning_sessions]),
        "learning_session_id",
    )

    items: list[MyPageReportItemResponse] = []
    for session in diagnostic_sessions:
        total_count, correct_count = diagnostic_counts.get(session["id"], (0, 0))
        if total_count == 0:
            continue

        items.append(
            MyPageReportItemResponse(
                report_type="diagnostic",
                session_id=session["id"],
                mode="diagnostic",
                status="completed",
                total_count=total_count,
                correct_count=correct_count,
                accuracy=_accuracy(correct_count, total_count),
                created_at=session["created_at"],
                completed_at=session.get("completed_at"),
            )
        )

    for session in learning_sessions:
        total_count, correct_count = learning_counts.get(session["id"], (0, 0))
        if total_count == 0:
            continue

        report_type, api_mode = LEARNING_MODE_METADATA[session["mode"]]
        items.append(
            MyPageReportItemResponse(
                report_type=report_type,
                session_id=session["id"],
                mode=api_mode,
                status="completed",
                total_count=total_count,
                correct_count=correct_count,
                accuracy=_accuracy(correct_count, total_count),
                created_at=session["created_at"],
                completed_at=session.get("completed_at"),
            )
        )

    items.sort(key=lambda item: item.completed_at or item.created_at, reverse=True)
    return MyPageReportsResponse(items=items)


def update_my_profile(
    learner_id: str,
    submission: ProfileUpdateRequest,
) -> Learner:
    """Persist the supplied mutable profile fields for the authenticated learner."""
    return update_learner_profile(
        learner_id,
        name=submission.name,
        age=submission.age,
    )
