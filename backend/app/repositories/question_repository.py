"""Queries for diagnostic questions and their public choice data."""

from typing import TypedDict

from app.db.supabase import supabase


class DiagnosticChoice(TypedDict):
    label: str
    text: str


class DiagnosticQuestion(TypedDict):
    id: str
    subtype_id: str
    part: str
    difficulty: str | None
    stem: str
    translation: str | None
    choices: list[DiagnosticChoice]


class PracticeChoice(TypedDict):
    label: str
    text: str


class PracticeQuestion(TypedDict):
    id: str
    subtype_id: str
    part: str
    difficulty: str | None
    stem: str
    translation: str | None
    choices: list[PracticeChoice]


class IncorrectChoiceTrap(TypedDict):
    choice_label: str
    trap_id: str | None


class DiagnosticQuestionGradingData(TypedDict):
    question_id: str
    found: bool
    subtype_id: str | None
    correct_choice_label: str | None
    incorrect_choice_traps: list[IncorrectChoiceTrap]


class PracticeQuestionGradingData(TypedDict):
    question_id: str
    found: bool
    subtype_id: str | None
    correct_choice_label: str | None
    incorrect_choice_traps: list[IncorrectChoiceTrap]


class ReviewQuestion(TypedDict):
    id: str
    subtype_id: str
    part: str
    difficulty: str | None
    stem: str
    translation: str | None
    choices: list[PracticeChoice]


class ReviewQuestionGradingData(TypedDict):
    question_id: str
    found: bool
    subtype_id: str | None
    correct_choice_label: str | None
    incorrect_choice_traps: list[IncorrectChoiceTrap]


def subtype_exists(subtype_id: str) -> bool:
    """Return whether a subtype exists in the taxonomy."""
    response = supabase.table("subtypes").select("id").eq("id", subtype_id).limit(1).execute()

    return bool(response.data)


def get_diagnostic_questions() -> list[DiagnosticQuestion]:
    """Return diagnostic questions with public-facing choices in A-D order.

    Grading fields such as ``is_correct`` and ``trap_id`` are intentionally not
    selected. A later grading-specific repository method can use its own return
    type without making those fields part of this public question structure.
    """
    response = (
        supabase.table("questions")
        .select(
            "id, subtype_id, part, difficulty, stem, translation, "
            "question_choices(choice_label, choice_text)"
        )
        .eq("question_type", "diagnostic")
        .order("id")
        .execute()
    )

    questions: list[DiagnosticQuestion] = []

    for row in response.data:
        choices = sorted(
            row.get("question_choices") or [],
            key=lambda choice: choice["choice_label"],
        )

        questions.append(
            {
                "id": row["id"],
                "subtype_id": row["subtype_id"],
                "part": row["part"],
                "difficulty": row["difficulty"],
                "stem": row["stem"],
                "translation": row["translation"],
                "choices": [
                    {
                        "label": choice["choice_label"],
                        "text": choice["choice_text"],
                    }
                    for choice in choices
                ],
            }
        )

    return questions


def get_practice_question_grading_data(
    question_id: str,
) -> PracticeQuestionGradingData:
    """Return internal grading data for one practice question."""
    response = (
        supabase.table("questions")
        .select("id, subtype_id, question_choices(choice_label, is_correct, trap_id)")
        .eq("question_type", "practice")
        .eq("id", question_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        return {
            "question_id": question_id,
            "found": False,
            "subtype_id": None,
            "correct_choice_label": None,
            "incorrect_choice_traps": [],
        }

    row = response.data[0]
    choices = row.get("question_choices") or []
    correct_choice_label = next(
        (choice["choice_label"] for choice in choices if choice["is_correct"]),
        None,
    )
    incorrect_choice_traps = sorted(
        [
            {
                "choice_label": choice["choice_label"],
                "trap_id": choice["trap_id"],
            }
            for choice in choices
            if not choice["is_correct"]
        ],
        key=lambda choice: choice["choice_label"],
    )

    return {
        "question_id": row["id"],
        "found": True,
        "subtype_id": row["subtype_id"],
        "correct_choice_label": correct_choice_label,
        "incorrect_choice_traps": incorrect_choice_traps,
    }


def get_practice_questions_grading_data(
    question_ids: list[str],
) -> list[PracticeQuestionGradingData]:
    """Return internal grading data for requested practice questions.

    Every requested ID is represented in the result. Missing IDs and IDs for
    non-practice questions are returned with ``found=False`` for service-layer
    validation.
    """
    if not question_ids:
        return []

    response = (
        supabase.table("questions")
        .select("id, subtype_id, question_choices(choice_label, is_correct, trap_id)")
        .eq("question_type", "practice")
        .in_("id", question_ids)
        .execute()
    )

    grading_data_by_question_id: dict[str, PracticeQuestionGradingData] = {}

    for row in response.data:
        choices = row.get("question_choices") or []
        correct_choice_label = next(
            (choice["choice_label"] for choice in choices if choice["is_correct"]),
            None,
        )
        incorrect_choice_traps = sorted(
            [
                {
                    "choice_label": choice["choice_label"],
                    "trap_id": choice["trap_id"],
                }
                for choice in choices
                if not choice["is_correct"]
            ],
            key=lambda choice: choice["choice_label"],
        )

        grading_data_by_question_id[row["id"]] = {
            "question_id": row["id"],
            "found": True,
            "subtype_id": row["subtype_id"],
            "correct_choice_label": correct_choice_label,
            "incorrect_choice_traps": incorrect_choice_traps,
        }

    return [
        grading_data_by_question_id.get(
            question_id,
            {
                "question_id": question_id,
                "found": False,
                "subtype_id": None,
                "correct_choice_label": None,
                "incorrect_choice_traps": [],
            },
        )
        for question_id in question_ids
    ]


def get_practice_questions_by_subtype(
    subtype_id: str,
) -> list[PracticeQuestion]:
    """Return public practice questions for one subtype in A-D choice order."""
    response = (
        supabase.table("questions")
        .select(
            "id, subtype_id, part, difficulty, stem, translation, "
            "question_choices(choice_label, choice_text)"
        )
        .eq("question_type", "practice")
        .eq("subtype_id", subtype_id)
        .order("id")
        .execute()
    )

    questions: list[PracticeQuestion] = []

    for row in response.data:
        choices = sorted(
            row.get("question_choices") or [],
            key=lambda choice: choice["choice_label"],
        )

        questions.append(
            {
                "id": row["id"],
                "subtype_id": row["subtype_id"],
                "part": row["part"],
                "difficulty": row["difficulty"],
                "stem": row["stem"],
                "translation": row["translation"],
                "choices": [
                    {
                        "label": choice["choice_label"],
                        "text": choice["choice_text"],
                    }
                    for choice in choices
                ],
            }
        )

    return questions


def get_practice_questions_by_area_codes(
    area_codes: list[str],
) -> list[PracticeQuestion]:
    """Return public practice questions filtered by their taxonomy areas."""
    if not area_codes:
        return []

    response = (
        supabase.table("questions")
        .select(
            "id, subtype_id, part, difficulty, stem, translation, "
            "question_choices(choice_label, choice_text), "
            "subtypes!inner(types!inner(area_code))"
        )
        .eq("question_type", "practice")
        .in_("subtypes.types.area_code", area_codes)
        .order("id")
        .execute()
    )

    questions: list[PracticeQuestion] = []

    for row in response.data:
        choices = sorted(
            row.get("question_choices") or [],
            key=lambda choice: choice["choice_label"],
        )

        questions.append(
            {
                "id": row["id"],
                "subtype_id": row["subtype_id"],
                "part": row["part"],
                "difficulty": row["difficulty"],
                "stem": row["stem"],
                "translation": row["translation"],
                "choices": [
                    {
                        "label": choice["choice_label"],
                        "text": choice["choice_text"],
                    }
                    for choice in choices
                ],
            }
        )

    return questions


def get_public_questions_by_ids(question_ids: list[str]) -> list[PracticeQuestion]:
    """Return public question data in the supplied question ID order."""
    if not question_ids:
        return []

    response = (
        supabase.table("questions")
        .select(
            "id, subtype_id, part, difficulty, stem, translation, "
            "question_choices(choice_label, choice_text)"
        )
        .eq("question_type", "practice")
        .in_("id", question_ids)
        .execute()
    )

    questions_by_id: dict[str, PracticeQuestion] = {}

    for row in response.data:
        choices = sorted(
            row.get("question_choices") or [],
            key=lambda choice: choice["choice_label"],
        )
        questions_by_id[row["id"]] = {
            "id": row["id"],
            "subtype_id": row["subtype_id"],
            "part": row["part"],
            "difficulty": row["difficulty"],
            "stem": row["stem"],
            "translation": row["translation"],
            "choices": [
                {
                    "label": choice["choice_label"],
                    "text": choice["choice_text"],
                }
                for choice in choices
            ],
        }

    return [
        questions_by_id[question_id]
        for question_id in question_ids
        if question_id in questions_by_id
    ]


def get_diagnostic_question_grading_data(
    question_ids: list[str],
) -> list[DiagnosticQuestionGradingData]:
    """Return internal grading data for the requested diagnostic questions.

    An item is returned for every requested ID. Missing or non-diagnostic IDs
    are marked with ``found=False`` so a later service can validate them.
    """
    if not question_ids:
        return []

    response = (
        supabase.table("questions")
        .select("id, subtype_id, question_choices(choice_label, is_correct, trap_id)")
        .eq("question_type", "diagnostic")
        .in_("id", question_ids)
        .execute()
    )

    grading_data_by_question_id: dict[str, DiagnosticQuestionGradingData] = {}

    for row in response.data:
        choices = row.get("question_choices") or []
        correct_choice_label = next(
            (choice["choice_label"] for choice in choices if choice["is_correct"]),
            None,
        )
        incorrect_choice_traps = sorted(
            [
                {
                    "choice_label": choice["choice_label"],
                    "trap_id": choice["trap_id"],
                }
                for choice in choices
                if not choice["is_correct"]
            ],
            key=lambda choice: choice["choice_label"],
        )

        grading_data_by_question_id[row["id"]] = {
            "question_id": row["id"],
            "found": True,
            "subtype_id": row["subtype_id"],
            "correct_choice_label": correct_choice_label,
            "incorrect_choice_traps": incorrect_choice_traps,
        }

    return [
        grading_data_by_question_id.get(
            question_id,
            {
                "question_id": question_id,
                "found": False,
                "subtype_id": None,
                "correct_choice_label": None,
                "incorrect_choice_traps": [],
            },
        )
        for question_id in question_ids
    ]


def get_public_toeic_questions_by_ids(question_ids: list[str]) -> list[ReviewQuestion]:
    """Return public diagnostic or practice questions in requested ID order."""
    if not question_ids:
        return []

    response = (
        supabase.table("questions")
        .select(
            "id, subtype_id, part, difficulty, stem, translation, "
            "question_choices(choice_label, choice_text)"
        )
        .in_("id", question_ids)
        .execute()
    )
    questions_by_id: dict[str, ReviewQuestion] = {}
    for row in response.data:
        choices = sorted(
            row.get("question_choices") or [],
            key=lambda choice: choice["choice_label"],
        )
        questions_by_id[row["id"]] = {
            "id": row["id"],
            "subtype_id": row["subtype_id"],
            "part": row["part"],
            "difficulty": row["difficulty"],
            "stem": row["stem"],
            "translation": row["translation"],
            "choices": [
                {"label": choice["choice_label"], "text": choice["choice_text"]}
                for choice in choices
            ],
        }

    return [
        questions_by_id[question_id]
        for question_id in question_ids
        if question_id in questions_by_id
    ]


def get_toeic_questions_grading_data(
    question_ids: list[str],
) -> list[ReviewQuestionGradingData]:
    """Return internal grading data for diagnostic or practice questions."""
    if not question_ids:
        return []

    response = (
        supabase.table("questions")
        .select("id, subtype_id, question_choices(choice_label, is_correct, trap_id)")
        .in_("id", question_ids)
        .execute()
    )
    by_question_id: dict[str, ReviewQuestionGradingData] = {}
    for row in response.data:
        choices = row.get("question_choices") or []
        by_question_id[row["id"]] = {
            "question_id": row["id"],
            "found": True,
            "subtype_id": row["subtype_id"],
            "correct_choice_label": next(
                (choice["choice_label"] for choice in choices if choice["is_correct"]),
                None,
            ),
            "incorrect_choice_traps": sorted(
                [
                    {
                        "choice_label": choice["choice_label"],
                        "trap_id": choice["trap_id"],
                    }
                    for choice in choices
                    if not choice["is_correct"]
                ],
                key=lambda choice: choice["choice_label"],
            ),
        }

    return [
        by_question_id.get(
            question_id,
            {
                "question_id": question_id,
                "found": False,
                "subtype_id": None,
                "correct_choice_label": None,
                "incorrect_choice_traps": [],
            },
        )
        for question_id in question_ids
    ]
