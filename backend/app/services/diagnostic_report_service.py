"""Calculation logic for diagnostic reports."""

from typing import TypedDict

from app.repositories.diagnostic_repository import (
    get_diagnostic_attempts_with_taxonomy,
)


class DiagnosticSubtypePerformance(TypedDict):
    subtype_id: str
    subtype_name: str
    type_id: str
    type_name: str
    attempted_count: int
    correct_count: int
    accuracy: float


class DiagnosticReport(TypedDict):
    total_count: int
    correct_count: int
    accuracy: float
    estimated_score: int | None
    strengths: list[DiagnosticSubtypePerformance]
    weaknesses: list[DiagnosticSubtypePerformance]
    recommended_learning_type: DiagnosticSubtypePerformance | None


def get_diagnostic_report(
    diagnostic_session_id: str,
    rank_limit: int = 2,
) -> DiagnosticReport:
    """Calculate subtype-level performance for one diagnostic session."""
    if rank_limit < 1:
        raise ValueError("rank_limit must be at least 1.")

    attempts = get_diagnostic_attempts_with_taxonomy(diagnostic_session_id)
    performances_by_subtype: dict[str, DiagnosticSubtypePerformance] = {}
    total_count = 0
    correct_count = 0

    for attempt in attempts:
        subtype_id = attempt["subtype_id"]
        subtype_name = attempt["subtype_name"]
        type_id = attempt["type_id"]
        type_name = attempt["type_name"]

        if None in (subtype_id, subtype_name, type_id, type_name):
            raise RuntimeError(
                "Diagnostic attempt is missing the subtype or type data required "
                f"for reporting: {attempt['question_id']}"
            )

        performance = performances_by_subtype.setdefault(
            subtype_id,
            {
                "subtype_id": subtype_id,
                "subtype_name": subtype_name,
                "type_id": type_id,
                "type_name": type_name,
                "attempted_count": 0,
                "correct_count": 0,
                "accuracy": 0.0,
            },
        )
        performance["attempted_count"] += 1
        total_count += 1

        if attempt["is_correct"]:
            performance["correct_count"] += 1
            correct_count += 1

    performances = list(performances_by_subtype.values())

    for performance in performances:
        performance["accuracy"] = round(
            performance["correct_count"] / performance["attempted_count"] * 100,
            2,
        )

    strengths = sorted(
        performances,
        key=lambda performance: (-performance["accuracy"], performance["subtype_id"]),
    )[:rank_limit]
    weaknesses = sorted(
        performances,
        key=lambda performance: (performance["accuracy"], performance["subtype_id"]),
    )[:rank_limit]

    return {
        "total_count": total_count,
        "correct_count": correct_count,
        "accuracy": round(correct_count / total_count * 100, 2) if total_count else 0.0,
        "estimated_score": None,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommended_learning_type": weaknesses[0] if weaknesses else None,
    }
