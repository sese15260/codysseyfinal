"""Deterministic long-term TOEIC learning-memory recommendations."""

from collections import defaultdict
from typing import Any

from app.repositories.learning_recommendation_repository import (
    LearnerRecommendationAttempt,
    get_learner_toeic_attempts,
)
from app.schemas.learning import (
    LearningRecommendationItemResponse,
    LearningRecommendationsResponse,
    LearningRecommendationSummaryResponse,
    LearningRecommendationTrapResponse,
    LearningStrengthItemResponse,
)

MIN_ATTEMPTS_FOR_CONFIDENCE = 2
RECENT_ATTEMPT_WINDOW = 3
MAX_RECOMMENDATIONS = 3
MAX_TOP_TRAPS = 3
WEAK_ACCURACY_WEIGHT = 0.6
CONFIDENT_SAMPLE_BONUS = 10.0
RECENT_WRONG_BONUS = 8.0
LAST_ATTEMPT_WRONG_BONUS = 10.0
CONSECUTIVE_RECENT_WRONG_BONUS = 4.0
REPEATED_TRAP_BONUS = 5.0
STRONG_ACCURACY_THRESHOLD = 80.0


def _top_traps(attempts: list[LearnerRecommendationAttempt]) -> list[dict[str, Any]]:
    """Aggregate wrong-answer traps for one subtype, with deterministic order."""
    trap_stats: dict[str, dict[str, Any]] = {}
    for attempt in attempts:
        trap_id = attempt["trap_id"]
        if attempt["is_correct"] or trap_id is None:
            continue
        stat = trap_stats.setdefault(
            trap_id,
            {
                "trap_id": trap_id,
                "name": attempt["trap_name"] or trap_id,
                "description": attempt["trap_description"],
                "wrong_count": 0,
                "last_seen_at": attempt["answered_at"],
            },
        )
        stat["wrong_count"] += 1

    return sorted(
        trap_stats.values(),
        key=lambda trap: (-trap["wrong_count"], trap["trap_id"]),
    )[:MAX_TOP_TRAPS]


def _subtype_stat(
    subtype_id: str,
    attempts: list[LearnerRecommendationAttempt],
) -> dict[str, Any]:
    """Calculate the complete deterministic memory record for one subtype."""
    newest_first = sorted(
        attempts,
        key=lambda attempt: (attempt["answered_at"], attempt["id"]),
        reverse=True,
    )
    newest = newest_first[0]
    total_attempts = len(newest_first)
    correct_count = sum(attempt["is_correct"] is True for attempt in newest_first)
    wrong_count = total_attempts - correct_count
    accuracy = round(correct_count / total_attempts * 100, 2)
    recent_attempts = newest_first[:RECENT_ATTEMPT_WINDOW]
    recent_wrong_count = sum(attempt["is_correct"] is False for attempt in recent_attempts)
    recent_wrong_streak = 0
    for attempt in recent_attempts:
        if attempt["is_correct"]:
            break
        recent_wrong_streak += 1
    top_traps = _top_traps(newest_first)
    repeated_trap_count = sum(
        1 for trap in top_traps if trap["wrong_count"] >= MIN_ATTEMPTS_FOR_CONFIDENCE
    )
    priority_score = (
        (100 - accuracy) * WEAK_ACCURACY_WEIGHT
        + CONFIDENT_SAMPLE_BONUS
        + recent_wrong_count * RECENT_WRONG_BONUS
        + (LAST_ATTEMPT_WRONG_BONUS if not newest["is_correct"] else 0)
        + recent_wrong_streak * CONSECUTIVE_RECENT_WRONG_BONUS
        + repeated_trap_count * REPEATED_TRAP_BONUS
    )
    return {
        "subtype_id": subtype_id,
        "subtype_name": newest["subtype_name"],
        "type_id": newest["type_id"],
        "type_name": newest["type_name"],
        "total_attempts": total_attempts,
        "correct_count": correct_count,
        "wrong_count": wrong_count,
        "accuracy": accuracy,
        "last_attempted_at": newest["answered_at"],
        "last_is_correct": newest["is_correct"],
        "recent_wrong_count": recent_wrong_count,
        "recent_wrong_streak": recent_wrong_streak,
        "top_traps": top_traps,
        "priority_score": round(priority_score, 2),
    }


def _has_complete_taxonomy(stat: dict[str, Any]) -> bool:
    return all(stat[key] for key in ("subtype_id", "subtype_name", "type_id", "type_name"))


def _recommendation_reasons(stat: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if stat["recent_wrong_streak"] >= 2:
        reasons.append(f"최근 {stat['recent_wrong_streak']}회 연속 오답")
    elif stat["recent_wrong_count"] >= 2:
        reasons.append(f"최근 {RECENT_ATTEMPT_WINDOW}회 중 {stat['recent_wrong_count']}회 오답")
    elif not stat["last_is_correct"]:
        reasons.append("가장 최근 풀이가 오답")
    reasons.append(f"누적 정답률 {stat['accuracy']:.2f}%")
    for trap in stat["top_traps"]:
        if trap["wrong_count"] >= MIN_ATTEMPTS_FOR_CONFIDENCE:
            reasons.append(f"{trap['trap_id']} 함정 {trap['wrong_count']}회 반복")
    return reasons


def get_learning_recommendations(learner_id: str) -> LearningRecommendationsResponse:
    """Analyze all learner attempts as long-term learning memory."""
    raw_attempts = get_learner_toeic_attempts(learner_id)
    attempts_by_subtype: dict[str, list[LearnerRecommendationAttempt]] = defaultdict(list)
    for attempt in raw_attempts:
        subtype_id = attempt["subtype_id"]
        if subtype_id is not None:
            attempts_by_subtype[subtype_id].append(attempt)

    stats = [
        _subtype_stat(subtype_id, attempts) for subtype_id, attempts in attempts_by_subtype.items()
    ]
    complete_stats = [stat for stat in stats if _has_complete_taxonomy(stat)]
    confident_stats = [
        stat for stat in complete_stats if stat["total_attempts"] >= MIN_ATTEMPTS_FOR_CONFIDENCE
    ]

    recommendation_candidates = [stat for stat in confident_stats if stat["wrong_count"] > 0]
    recommendation_candidates.sort(
        key=lambda stat: (-stat["priority_score"], stat["subtype_id"]),
    )
    selected_recommendations = recommendation_candidates[:MAX_RECOMMENDATIONS]
    selected_subtype_ids = {stat["subtype_id"] for stat in selected_recommendations}

    strength_candidates = [
        stat
        for stat in confident_stats
        if (
            stat["subtype_id"] not in selected_subtype_ids
            and stat["accuracy"] >= STRONG_ACCURACY_THRESHOLD
            and stat["last_is_correct"]
        )
    ]
    strength_candidates.sort(
        key=lambda stat: (-stat["accuracy"], -stat["total_attempts"], stat["subtype_id"]),
    )

    recommendations = [
        LearningRecommendationItemResponse(
            **{
                **stat,
                "top_traps": [
                    LearningRecommendationTrapResponse(**trap) for trap in stat["top_traps"]
                ],
                "reason": _recommendation_reasons(stat),
            }
        )
        for stat in selected_recommendations
    ]
    strengths = [
        LearningStrengthItemResponse(
            subtype_id=stat["subtype_id"],
            subtype_name=stat["subtype_name"],
            type_id=stat["type_id"],
            type_name=stat["type_name"],
            total_attempts=stat["total_attempts"],
            correct_count=stat["correct_count"],
            wrong_count=stat["wrong_count"],
            accuracy=stat["accuracy"],
            last_attempted_at=stat["last_attempted_at"],
            last_is_correct=stat["last_is_correct"],
            reason=[
                f"누적 정답률 {stat['accuracy']:.2f}%",
                "가장 최근 풀이가 정답",
            ],
        )
        for stat in strength_candidates[:MAX_RECOMMENDATIONS]
    ]
    return LearningRecommendationsResponse(
        recommendations=recommendations,
        strengths=strengths,
        summary=LearningRecommendationSummaryResponse(
            total_attempts=len(raw_attempts),
            analyzed_subtypes=len(complete_stats),
        ),
    )
