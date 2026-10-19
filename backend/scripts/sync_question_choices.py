"""Synchronize existing question choices with the current question-bank JSON.

This script updates only ``choice_text``, ``is_correct``, and ``trap_id`` on
existing ``question_choices`` rows. It never inserts or deletes rows and does
not modify the questions or taxonomy tables.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.db.supabase import supabase

BASE_DIR = Path(__file__).resolve().parent.parent
DIAGNOSTIC_PATH = BASE_DIR / "data" / "bank" / "diagnostic.json"
PRACTICE_PATH = BASE_DIR / "data" / "bank" / "practice.json"
CHOICE_LABELS = ("A", "B", "C", "D")


class SynchronizationError(RuntimeError):
    """Raised when JSON or database state is unsafe to synchronize."""


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def build_expected_choices() -> list[dict[str, Any]]:
    """Build the 324 expected choice payloads from both question-bank files."""
    diagnostic_questions = load_json(DIAGNOSTIC_PATH).get("items")
    practice_pool = load_json(PRACTICE_PATH).get("pool")

    if not isinstance(diagnostic_questions, list):
        raise SynchronizationError("diagnostic.json must contain an items list.")
    if not isinstance(practice_pool, dict):
        raise SynchronizationError("practice.json must contain a pool object.")

    practice_questions = [
        question for questions in practice_pool.values() for question in questions
    ]
    questions = diagnostic_questions + practice_questions

    if len(questions) != 81:
        raise SynchronizationError(
            f"Expected 81 questions in the JSON banks, found {len(questions)}."
        )

    question_ids = [question.get("id") for question in questions]
    if len(question_ids) != len(set(question_ids)):
        raise SynchronizationError("Question-bank JSON contains duplicate question IDs.")

    choices: list[dict[str, Any]] = []

    for question in questions:
        question_id = question.get("id")
        options = question.get("options")
        answer = question.get("answer")
        option_traps = question.get("option_traps")

        if not isinstance(question_id, str):
            raise SynchronizationError("Question-bank JSON contains an invalid question ID.")
        if not isinstance(options, dict) or set(options) != set(CHOICE_LABELS):
            raise SynchronizationError(
                f"{question_id}: options must contain exactly A, B, C, and D."
            )
        if answer not in CHOICE_LABELS:
            raise SynchronizationError(f"{question_id}: answer must be A, B, C, or D.")
        if not isinstance(option_traps, dict) or set(option_traps) != (
            set(CHOICE_LABELS) - {answer}
        ):
            raise SynchronizationError(
                f"{question_id}: option_traps must contain exactly the three wrong labels."
            )

        for choice_label in CHOICE_LABELS:
            choices.append(
                {
                    "question_id": question_id,
                    "choice_label": choice_label,
                    "choice_text": options[choice_label],
                    "is_correct": choice_label == answer,
                    "trap_id": None if choice_label == answer else option_traps[choice_label],
                }
            )

    if len(choices) != 324:
        raise SynchronizationError(
            f"Expected 324 choices from the JSON banks, found {len(choices)}."
        )

    return choices


def validate_database_structure(question_ids: list[str]) -> list[dict[str, Any]]:
    """Ensure every target question has exactly one A-D choice row."""
    question_response = supabase.table("questions").select("id").in_("id", question_ids).execute()
    existing_question_ids = {row["id"] for row in question_response.data}
    missing_question_ids = sorted(set(question_ids) - existing_question_ids)

    if missing_question_ids:
        raise SynchronizationError(
            "Target questions are missing from the database: " + ", ".join(missing_question_ids)
        )

    choices_response = (
        supabase.table("question_choices")
        .select("question_id, choice_label, choice_text, is_correct, trap_id")
        .in_("question_id", question_ids)
        .execute()
    )
    database_choices = choices_response.data

    if len(database_choices) != 324:
        raise SynchronizationError(
            "Target questions must have exactly 324 choice rows in total; "
            f"found {len(database_choices)}."
        )

    choices_by_question_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for choice in database_choices:
        choices_by_question_id[choice["question_id"]].append(choice)

    for question_id in question_ids:
        choices = choices_by_question_id.get(question_id, [])
        labels = [choice["choice_label"] for choice in choices]

        if len(choices) != 4:
            raise SynchronizationError(
                f"{question_id}: expected 4 choice rows, found {len(choices)}."
            )
        if set(labels) != set(CHOICE_LABELS) or len(set(labels)) != 4:
            raise SynchronizationError(
                f"{question_id}: choice labels must be exactly A, B, C, and D."
            )

    return database_choices


def get_changes(
    expected_choices: list[dict[str, Any]],
    database_choices: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], list[str]]]:
    """Return expected payloads whose synchronized fields differ from the DB."""
    database_by_key = {
        (choice["question_id"], choice["choice_label"]): choice for choice in database_choices
    }
    changes: list[tuple[dict[str, Any], list[str]]] = []

    for expected in expected_choices:
        key = (expected["question_id"], expected["choice_label"])
        database_choice = database_by_key.get(key)
        if database_choice is None:
            raise SynchronizationError(f"{key[0]} / {key[1]}: expected database row is missing.")

        changed_fields = [
            field
            for field in ("choice_text", "is_correct", "trap_id")
            if database_choice[field] != expected[field]
        ]
        if changed_fields:
            changes.append((expected, changed_fields))

    return changes


def print_change_summary(
    changes: list[tuple[dict[str, Any], list[str]]],
    sample_limit: int,
) -> None:
    """Print a concise difference summary without exposing full choice text."""
    affected_questions = {choice["question_id"] for choice, _ in changes}
    print("target choices: 324")
    print(f"changes required: {len(changes)}")
    print(f"already matching: {324 - len(changes)}")
    print(f"affected questions: {len(affected_questions)}")

    if not changes or sample_limit == 0:
        return

    print("\nChange samples:")
    for choice, changed_fields in changes[:sample_limit]:
        print(
            f"- {choice['question_id']} / {choice['choice_label']}: "
            + ", ".join(f"{field} changed" for field in changed_fields)
        )

    remaining = len(changes) - sample_limit
    if remaining > 0:
        print(f"- ... {remaining} additional changed choices")


def update_choices(changes: list[tuple[dict[str, Any], list[str]]]) -> None:
    """Update only changed fields on existing rows identified by composite key."""
    for expected, changed_fields in changes:
        payload = {field: expected[field] for field in changed_fields}
        (
            supabase.table("question_choices")
            .update(payload)
            .eq("question_id", expected["question_id"])
            .eq("choice_label", expected["choice_label"])
            .execute()
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synchronize existing question_choices rows with question-bank JSON."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compare JSON and DB without updating any rows.",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=20,
        help="Maximum changed-choice samples to print (default: 20).",
    )
    args = parser.parse_args()

    if args.sample_limit < 0:
        raise SynchronizationError("--sample-limit must be zero or greater.")

    expected_choices = build_expected_choices()
    question_ids = sorted({choice["question_id"] for choice in expected_choices})
    print(f"target questions: {len(question_ids)}")

    database_choices = validate_database_structure(question_ids)
    changes = get_changes(expected_choices, database_choices)
    print_change_summary(changes, args.sample_limit)

    if args.dry_run:
        print("\nDRY RUN: no database rows updated.")
        return

    if changes:
        print("\nUpdating changed question_choices rows...")
        update_choices(changes)
    else:
        print("\nNo updates required.")

    verified_choices = validate_database_structure(question_ids)
    remaining_changes = get_changes(expected_choices, verified_choices)
    if remaining_changes:
        raise SynchronizationError(
            f"Post-update verification failed: {len(remaining_changes)} choices differ."
        )

    print("Post-update verification passed: all 324 choices match the JSON banks.")


if __name__ == "__main__":
    try:
        main()
    except SynchronizationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1) from error
