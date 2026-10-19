"""Application rules for a learner's fixed daily vocabulary assignments."""

import random
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.repositories.vocabulary_repository import (
    create_daily_assignments,
    ensure_learner_word,
    get_all_vocabulary_words,
    get_daily_assignments,
    get_learner_word_states,
    get_memorized_word_ids_for_learner,
    get_saved_words_for_learner,
    get_word_by_id,
    get_words_by_ids,
    update_learner_word_fields,
)
from app.schemas.vocabulary import (
    SavedWordResponse,
    SavedWordsResponse,
    TodayWordResponse,
    TodayWordsResponse,
    WordStateResponse,
)

DAILY_WORD_LIMIT = 30
SEOUL_TIMEZONE = ZoneInfo("Asia/Seoul")


class WordNotFoundError(ValueError):
    """Raised when a requested shared vocabulary word does not exist."""


def _today_in_seoul() -> str:
    """Return the service's daily-assignment date in Korea Standard Time."""
    return datetime.now(SEOUL_TIMEZONE).date().isoformat()


def _visible_assignment_ids(
    assignments: list[dict[str, object]],
    memorized_word_ids: set[str],
) -> list[str]:
    """Keep assigned IDs in stable order while hiding now-memorized words."""
    return [
        assignment["word_id"]
        for assignment in assignments
        if isinstance(assignment.get("word_id"), str)
        and assignment["word_id"] not in memorized_word_ids
    ]


def get_today_words(learner_id: str) -> TodayWordsResponse:
    """Return up to 30 stable, non-memorized words for the current Seoul date."""
    assigned_date = _today_in_seoul()
    assignments = get_daily_assignments(learner_id, assigned_date)
    memorized_word_ids = get_memorized_word_ids_for_learner(learner_id)
    visible_word_ids = _visible_assignment_ids(assignments, memorized_word_ids)

    if len(visible_word_ids) < DAILY_WORD_LIMIT:
        assigned_word_ids = {
            assignment["word_id"]
            for assignment in assignments
            if isinstance(assignment.get("word_id"), str)
        }
        candidate_words = [
            word
            for word in get_all_vocabulary_words()
            if word["id"] not in assigned_word_ids and word["id"] not in memorized_word_ids
        ]
        selection_count = min(
            DAILY_WORD_LIMIT - len(visible_word_ids),
            len(candidate_words),
        )
        if selection_count:
            selected_words = random.sample(candidate_words, selection_count)
            create_daily_assignments(
                learner_id=learner_id,
                word_ids=[word["id"] for word in selected_words],
                assigned_date=assigned_date,
            )

            # A re-read makes the database assignment the source of truth after
            # a conflict-safe concurrent insert.
            assignments = get_daily_assignments(learner_id, assigned_date)
            visible_word_ids = _visible_assignment_ids(
                assignments,
                memorized_word_ids,
            )

    visible_word_ids = visible_word_ids[:DAILY_WORD_LIMIT]
    words_by_id = {word["id"]: word for word in get_words_by_ids(visible_word_ids)}
    states_by_word_id = {
        state["word_id"]: state for state in get_learner_word_states(learner_id, visible_word_ids)
    }

    words = [
        TodayWordResponse(
            id=word_id,
            word=words_by_id[word_id]["word"],
            meaning=words_by_id[word_id]["meaning"],
            example=words_by_id[word_id]["example"],
            difficulty=words_by_id[word_id]["difficulty"],
            is_saved=bool(states_by_word_id.get(word_id, {}).get("is_saved", False)),
            is_memorized=bool(states_by_word_id.get(word_id, {}).get("is_memorized", False)),
        )
        for word_id in visible_word_ids
        if word_id in words_by_id
    ]

    return TodayWordsResponse(
        date=assigned_date,
        total_count=len(words),
        words=words,
    )


def _current_timestamp() -> str:
    """Return an aware UTC timestamp for mutable learner-word state."""
    return datetime.now(timezone.utc).isoformat()


def _update_word_state(
    learner_id: str,
    word_id: str,
    fields: dict[str, bool | str | None],
) -> WordStateResponse:
    """Validate a shared word, ensure learner state, then update selected fields."""
    if get_word_by_id(word_id) is None:
        raise WordNotFoundError("Word not found.")

    ensure_learner_word(learner_id, word_id)
    state = update_learner_word_fields(learner_id, word_id, fields)
    return WordStateResponse(
        word_id=state["word_id"],
        is_saved=state["is_saved"],
        is_memorized=state["is_memorized"],
        saved_at=state["saved_at"],
        memorized_at=state["memorized_at"],
    )


def set_saved_status(
    learner_id: str,
    word_id: str,
    is_saved: bool,
) -> WordStateResponse:
    """Set save state without modifying the word's memorized state."""
    return _update_word_state(
        learner_id,
        word_id,
        {
            "is_saved": is_saved,
            "saved_at": _current_timestamp() if is_saved else None,
        },
    )


def set_memorized_status(
    learner_id: str,
    word_id: str,
    is_memorized: bool,
) -> WordStateResponse:
    """Set memorized state without modifying the word's saved state."""
    return _update_word_state(
        learner_id,
        word_id,
        {
            "is_memorized": is_memorized,
            "memorized_at": _current_timestamp() if is_memorized else None,
        },
    )


def get_saved_words(learner_id: str) -> SavedWordsResponse:
    """Return all saved words for one learner, including memorized saved words."""
    words: list[SavedWordResponse] = []
    for record in get_saved_words_for_learner(learner_id):
        vocabulary_word = record.get("vocabulary_words")
        if not isinstance(vocabulary_word, dict):
            # A vocabulary-word deletion cascades learner state; this only guards
            # against unexpected inconsistent data without leaking it to clients.
            continue

        words.append(
            SavedWordResponse(
                id=vocabulary_word["id"],
                word=vocabulary_word["word"],
                meaning=vocabulary_word["meaning"],
                example=vocabulary_word.get("example"),
                difficulty=vocabulary_word.get("difficulty"),
                is_saved=record["is_saved"],
                is_memorized=record["is_memorized"],
                saved_at=record.get("saved_at"),
                memorized_at=record.get("memorized_at"),
            )
        )

    return SavedWordsResponse(total_count=len(words), words=words)
