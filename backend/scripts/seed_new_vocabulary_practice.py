"""Incrementally seed the new vocabulary practice questions and choices."""

import argparse
import json
from pathlib import Path

from app.db.supabase import supabase

BASE_DIR = Path(__file__).resolve().parent.parent
PRACTICE_PATH = BASE_DIR / "data" / "bank" / "practice.json"

TARGET_QUESTION_IDS = (
    "LXV-01-01-p1",
    "LXV-01-01-p2",
    "LXN-01-01-p1",
    "LXN-01-01-p2",
    "LXA-01-01-p1",
    "LXA-01-01-p2",
    "LXA-02-01-p1",
    "LXA-02-01-p2",
    "LXD-01-01-p1",
    "LXD-01-01-p2",
    "LXD-02-01-p1",
    "LXD-02-01-p2",
    "LXD-04-01-p1",
    "LXD-04-01-p2",
    "LXD-04-02-p1",
    "LXD-04-02-p2",
    "LXD-04-03-p1",
    "LXD-04-03-p2",
)

EXPECTED_EXISTING_QUESTION_COUNT = 63
EXPECTED_EXISTING_CHOICE_COUNT = 252
EXPECTED_CHOICE_LABELS = {"A", "B", "C", "D"}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_target_questions() -> list[dict]:
    """Load and validate only the explicitly approved vocabulary questions."""
    if len(TARGET_QUESTION_IDS) != len(set(TARGET_QUESTION_IDS)):
        raise RuntimeError("Target question IDs must be unique.")

    practice_data = load_json(PRACTICE_PATH)
    selected_questions = [
        question
        for questions in practice_data["pool"].values()
        for question in questions
        if question["id"] in TARGET_QUESTION_IDS
    ]

    if len(selected_questions) != len(TARGET_QUESTION_IDS):
        raise RuntimeError("Target vocabulary practice question count is invalid.")

    questions_by_id = {question["id"]: question for question in selected_questions}

    missing_ids = set(TARGET_QUESTION_IDS) - questions_by_id.keys()
    if missing_ids:
        raise RuntimeError(
            "Expected vocabulary practice questions are missing: " + ", ".join(sorted(missing_ids))
        )

    if len(questions_by_id) != len(TARGET_QUESTION_IDS):
        raise RuntimeError("Target vocabulary practice question IDs are duplicated.")

    questions = [questions_by_id[question_id] for question_id in TARGET_QUESTION_IDS]

    for question in questions:
        option_labels = set(question["options"])
        answer = question["answer"]
        trap_labels = set(question.get("option_traps", {}))

        if option_labels != EXPECTED_CHOICE_LABELS:
            raise RuntimeError(f"Question {question['id']} must have exactly A-D choices.")

        if answer not in option_labels:
            raise RuntimeError(f"Question {question['id']} has an answer outside its choices.")

        if trap_labels != option_labels - {answer}:
            raise RuntimeError(
                f"Question {question['id']} must define traps for its three incorrect choices."
            )

    return questions


def build_rows(questions: list[dict]) -> tuple[list[dict], list[dict]]:
    """Build question and choice rows using the same shape as the full seed."""
    question_rows = []
    choice_rows = []

    for question in questions:
        question_rows.append(
            {
                "id": question["id"],
                "subtype_id": question["subtype_id"],
                "question_type": ("diagnostic" if question["id"].endswith("-dg") else "practice"),
                "part": "PART 5",
                "difficulty": question.get("difficulty"),
                "stem": question["stem"],
                "explanation": None,
                "translation": question.get("translation"),
                "source": question.get("source"),
                "verified": question.get("verified", False),
            }
        )

        for label, text in question["options"].items():
            choice_rows.append(
                {
                    "question_id": question["id"],
                    "choice_label": label,
                    "choice_text": text,
                    "is_correct": label == question["answer"],
                    "trap_id": question["option_traps"].get(label),
                }
            )

    expected_choice_count = len(questions) * len(EXPECTED_CHOICE_LABELS)
    if len(choice_rows) != expected_choice_count:
        raise RuntimeError("Target vocabulary practice choice count is invalid.")

    return question_rows, choice_rows


def get_existing_question_ids(question_ids: tuple[str, ...]) -> list[str]:
    """Return target question IDs that already exist in Supabase."""
    response = supabase.table("questions").select("id").in_("id", list(question_ids)).execute()
    return sorted(row["id"] for row in (response.data or []))


def print_summary(question_rows: list[dict], choice_rows: list[dict]) -> None:
    print("\n===== NEW VOCABULARY PRACTICE SEED SUMMARY =====")
    print("target questions:", len(question_rows))
    print("target choices:", len(choice_rows))
    print(
        "final expected questions:",
        EXPECTED_EXISTING_QUESTION_COUNT + len(question_rows),
    )
    print(
        "final expected question_choices:",
        EXPECTED_EXISTING_CHOICE_COUNT + len(choice_rows),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="DB에 저장하지 않고 대상 데이터와 예상 개수만 확인합니다.",
    )
    args = parser.parse_args()

    questions = get_target_questions()
    question_rows, choice_rows = build_rows(questions)
    print_summary(question_rows, choice_rows)

    if args.dry_run:
        print("\nDRY RUN: no database reads or writes performed.")
        return

    existing_question_ids = get_existing_question_ids(TARGET_QUESTION_IDS)
    if existing_question_ids:
        raise RuntimeError(
            "Aborting seed because target question IDs already exist: "
            + ", ".join(existing_question_ids)
        )

    print("\nInserting questions:", len(question_rows))
    supabase.table("questions").insert(question_rows).execute()

    print("Inserting question_choices:", len(choice_rows))
    supabase.table("question_choices").insert(choice_rows).execute()

    print("\nNew vocabulary practice seed completed successfully.")


if __name__ == "__main__":
    main()
