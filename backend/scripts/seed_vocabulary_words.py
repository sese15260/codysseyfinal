"""Seed shared TOEIC vocabulary words without overwriting existing rows."""

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
WORDS_PATH = BASE_DIR / "data" / "vocabulary" / "words.json"
ALLOWED_DIFFICULTIES = {"basic", "intermediate", "advanced"}
REQUIRED_FIELDS = {"word", "meaning", "example", "difficulty"}


def load_words(path: Path = WORDS_PATH) -> list[dict[str, str]]:
    """Load and validate the checked-in vocabulary source file."""
    with path.open(encoding="utf-8") as file:
        words: Any = json.load(file)

    if not isinstance(words, list):
        raise ValueError("Vocabulary seed data must be a JSON array.")

    normalized_words: list[dict[str, str]] = []
    seen_words: set[str] = set()
    for index, item in enumerate(words, start=1):
        if not isinstance(item, dict) or set(item) != REQUIRED_FIELDS:
            raise ValueError(f"Vocabulary item {index} must have {sorted(REQUIRED_FIELDS)}.")

        normalized_item: dict[str, str] = {}
        for field in REQUIRED_FIELDS:
            value = item[field]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Vocabulary item {index} has a blank {field}.")
            normalized_item[field] = value.strip()

        if normalized_item["difficulty"] not in ALLOWED_DIFFICULTIES:
            raise ValueError(
                f"Vocabulary item {index} has an unsupported difficulty: "
                f"{normalized_item['difficulty']}"
            )

        normalized_word = normalized_item["word"].casefold()
        if normalized_word in seen_words:
            raise ValueError(f"Duplicate vocabulary word: {normalized_item['word']}")
        seen_words.add(normalized_word)
        normalized_words.append(normalized_item)

    return normalized_words


def print_summary(words: list[dict[str, str]], *, dry_run: bool) -> None:
    """Print the validated input summary without exposing database credentials."""
    distribution = Counter(word["difficulty"] for word in words)
    print("Vocabulary words:", len(words))
    for difficulty in sorted(ALLOWED_DIFFICULTIES):
        print(f"{difficulty}: {distribution[difficulty]}")
    if dry_run:
        print("DRY RUN: no database reads or writes performed.")


def get_existing_normalized_words() -> set[str]:
    """Read existing word strings so seed rows can be skipped, never overwritten."""
    from app.db.supabase import supabase

    response = supabase.table("vocabulary_words").select("word").execute()
    return {row["word"].casefold() for row in response.data if isinstance(row.get("word"), str)}


def insert_missing_words(words: list[dict[str, str]]) -> tuple[int, int]:
    """Insert only source words absent from the database, preserving existing rows."""
    from app.db.supabase import supabase

    existing_words = get_existing_normalized_words()
    rows_to_insert = [word for word in words if word["word"].casefold() not in existing_words]
    skipped_count = len(words) - len(rows_to_insert)

    if rows_to_insert:
        supabase.table("vocabulary_words").insert(rows_to_insert).execute()

    return len(rows_to_insert), skipped_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed shared TOEIC vocabulary words into vocabulary_words."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate source data and print counts without accessing Supabase.",
    )
    args = parser.parse_args()

    words = load_words()
    print_summary(words, dry_run=args.dry_run)

    if args.dry_run:
        return

    inserted_count, skipped_count = insert_missing_words(words)
    print(f"Inserted: {inserted_count}")
    print(f"Skipped existing: {skipped_count}")


if __name__ == "__main__":
    main()
