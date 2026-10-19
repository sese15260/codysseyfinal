import argparse
import json
from pathlib import Path

from app.db.supabase import supabase

BASE_DIR = Path(__file__).resolve().parent.parent

TYPES_PATH = BASE_DIR / "data" / "taxonomy" / "types.json"
SPECS_PATH = BASE_DIR / "data" / "taxonomy" / "specs.json"
DIAGNOSTIC_PATH = BASE_DIR / "data" / "bank" / "diagnostic.json"
PRACTICE_PATH = BASE_DIR / "data" / "bank" / "practice.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def build_seed_data():
    types_data = load_json(TYPES_PATH)
    specs_data = load_json(SPECS_PATH)
    diagnostic_data = load_json(DIAGNOSTIC_PATH)
    practice_data = load_json(PRACTICE_PATH)

    raw_types = types_data["types"]
    raw_specs = specs_data["specs"]
    diagnostic_questions = diagnostic_data["items"]
    practice_pool = practice_data["pool"]

    # -----------------------------
    # types
    # -----------------------------
    types = []

    for item in raw_types:
        types.append(
            {
                "id": item["id"],
                "name": item["name"],
                "description": None,
                "group_code": item.get("group"),
                "area_code": item.get("area"),
                "weight": item.get("weight"),
                "rule": item.get("rule"),
            }
        )

    # -----------------------------
    # subtypes
    # -----------------------------
    subtypes = []

    for type_item in raw_types:
        for subtype in type_item.get("subtypes", []):
            subtypes.append(
                {
                    "id": subtype["id"],
                    "type_id": type_item["id"],
                    "name": subtype["name"],
                    "description": None,
                }
            )

    # -----------------------------
    # subtype specs
    # -----------------------------
    subtype_specs = []

    for subtype_id, spec in raw_specs.items():
        subtype_specs.append(
            {
                "subtype_id": subtype_id,
                "answer_rule": spec.get("answer_rule"),
                "cues": spec.get("cues", []),
                "judgment": spec.get("judgment"),
                "scope": spec.get("scope"),
                "option_pattern": spec.get("option_pattern"),
                "difficulty_default": spec.get("difficulty_default"),
                "distractors": spec.get("distractors", []),
                "vocab": spec.get("vocab"),
                "example_item": spec.get("example_item"),
                "notes": spec.get("notes"),
            }
        )

    # -----------------------------
    # traps
    # -----------------------------
    trap_values = types_data.get("item_attributes", {}).get("traps", {}).get("values", {})

    traps = []

    for trap_id, trap_name in trap_values.items():
        traps.append(
            {
                "id": trap_id,
                "name": trap_name,
                "description": None,
            }
        )

    # -----------------------------
    # practice 펼치기
    # -----------------------------
    practice_questions = []

    for _, questions in practice_pool.items():
        practice_questions.extend(questions)

    all_questions = diagnostic_questions + practice_questions

    # -----------------------------
    # questions
    # -----------------------------
    questions = []

    for question in all_questions:
        questions.append(
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

    # -----------------------------
    # choices
    # -----------------------------
    choices = []

    for question in all_questions:
        answer = question["answer"]
        option_traps = question.get("option_traps", {})

        for label, text in question["options"].items():
            choices.append(
                {
                    "question_id": question["id"],
                    "choice_label": label,
                    "choice_text": text,
                    "is_correct": label == answer,
                    "trap_id": option_traps.get(label),
                }
            )

    return {
        "types": types,
        "subtypes": subtypes,
        "subtype_specs": subtype_specs,
        "traps": traps,
        "questions": questions,
        "question_choices": choices,
    }


def print_summary(data):
    print("\n===== SEED SUMMARY =====")
    print("types:", len(data["types"]))
    print("subtypes:", len(data["subtypes"]))
    print("subtype_specs:", len(data["subtype_specs"]))
    print("traps:", len(data["traps"]))
    print("questions:", len(data["questions"]))
    print("question_choices:", len(data["question_choices"]))


def seed_table(table_name, rows):
    if not rows:
        return

    print(f"Seeding {table_name}: {len(rows)} rows")

    supabase.table(table_name).upsert(rows).execute()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="DB에 저장하지 않고 데이터 개수만 확인합니다.",
    )

    args = parser.parse_args()

    data = build_seed_data()

    print_summary(data)

    if args.dry_run:
        print("\nDRY RUN: no data inserted.")
        return

    seed_table("types", data["types"])
    seed_table("subtypes", data["subtypes"])
    seed_table("subtype_specs", data["subtype_specs"])
    seed_table("traps", data["traps"])
    seed_table("questions", data["questions"])
    seed_table("question_choices", data["question_choices"])

    print("\nSeed completed successfully.")


if __name__ == "__main__":
    main()
