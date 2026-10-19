"""Application rules for fixed saved-word vocabulary quizzes."""

import random
from datetime import datetime, timezone

from app.repositories.vocabulary_quiz_repository import (
    complete_vocabulary_quiz_session,
    create_vocabulary_quiz_attempts,
    create_vocabulary_quiz_items,
    create_vocabulary_quiz_session,
    get_vocabulary_quiz_items,
    get_vocabulary_quiz_session,
)
from app.repositories.vocabulary_repository import (
    get_all_vocabulary_words,
    get_saved_vocabulary_words_for_learner,
)
from app.schemas.vocabulary import (
    VocabularyQuizAnswerSubmission,
    VocabularyQuizItemResponse,
    VocabularyQuizItemsResponse,
    VocabularyQuizResultResponse,
    VocabularyQuizStartResponse,
    VocabularyQuizSubmitRequest,
    VocabularyQuizSubmitResponse,
)

QUIZ_WORD_LIMIT = 10


class NoSavedWordsError(ValueError):
    """Raised when a learner has no saved words to quiz."""


class VocabularyQuizNotFoundError(ValueError):
    """Raised for a missing or non-owned vocabulary quiz session."""


def _select_distractor_meanings(
    correct_word: dict[str, object],
    vocabulary_words: list[dict[str, object]],
) -> list[str]:
    """Choose three distinct meanings, preferring the correct word's difficulty."""
    correct_meaning = correct_word["meaning"]
    same_difficulty = [
        word
        for word in vocabulary_words
        if word["id"] != correct_word["id"]
        and word["difficulty"] == correct_word["difficulty"]
        and word["meaning"] != correct_meaning
    ]
    all_other_words = [
        word
        for word in vocabulary_words
        if word["id"] != correct_word["id"] and word["meaning"] != correct_meaning
    ]

    meanings: list[str] = []
    for word in random.sample(same_difficulty, len(same_difficulty)) + random.sample(
        all_other_words,
        len(all_other_words),
    ):
        meaning = word["meaning"]
        if meaning not in meanings:
            meanings.append(meaning)
        if len(meanings) == 3:
            return meanings

    raise RuntimeError("Not enough distinct vocabulary meanings for quiz choices.")


def _get_owned_session(session_id: str, learner_id: str) -> dict[str, object]:
    """Return a session only when it belongs to the current learner."""
    session = get_vocabulary_quiz_session(session_id)
    if session is None or session["learner_id"] != learner_id:
        raise VocabularyQuizNotFoundError("Vocabulary quiz session not found.")
    return session


def start_vocabulary_quiz(learner_id: str) -> VocabularyQuizStartResponse:
    """Select up to ten saved words and persist fixed questions and choices."""
    saved_words = get_saved_vocabulary_words_for_learner(learner_id)
    if not saved_words:
        raise NoSavedWordsError("No saved words available for quiz.")

    selected_words = random.sample(saved_words, min(QUIZ_WORD_LIMIT, len(saved_words)))
    vocabulary_words = get_all_vocabulary_words()
    item_templates: list[dict[str, object]] = []

    for position, word in enumerate(selected_words, start=1):
        choices = _select_distractor_meanings(word, vocabulary_words) + [word["meaning"]]
        random.shuffle(choices)
        item_templates.append(
            {
                "word_id": word["id"],
                "position": position,
                "correct_meaning": word["meaning"],
                "choices": choices,
            }
        )

    # Build all choices before writing the session so a source-data error does
    # not leave an empty in-progress quiz session behind.
    session_id = create_vocabulary_quiz_session(learner_id)
    quiz_items = [{"session_id": session_id, **item_template} for item_template in item_templates]
    create_vocabulary_quiz_items(session_id, quiz_items)
    return VocabularyQuizStartResponse(session_id=session_id, total_count=len(quiz_items))


def get_vocabulary_quiz_items_for_learner(
    session_id: str,
    learner_id: str,
) -> VocabularyQuizItemsResponse:
    """Return fixed public quiz items without revealing correct meanings."""
    _get_owned_session(session_id, learner_id)
    stored_items = get_vocabulary_quiz_items(session_id)
    items: list[VocabularyQuizItemResponse] = []
    for item in stored_items:
        word = (item.get("vocabulary_words") or {}).get("word")
        if not isinstance(word, str):
            raise RuntimeError("Vocabulary quiz item is missing its word.")
        items.append(
            VocabularyQuizItemResponse(
                word_id=item["word_id"],
                word=word,
                choices=item["choices"],
            )
        )
    return VocabularyQuizItemsResponse(
        session_id=session_id,
        total_count=len(items),
        items=items,
    )


def submit_vocabulary_quiz(
    submission: VocabularyQuizSubmitRequest,
    learner_id: str,
) -> VocabularyQuizSubmitResponse:
    """Validate a complete submission, grade it, persist attempts, and complete it."""
    session = _get_owned_session(submission.session_id, learner_id)
    if session["status"] != "in_progress":
        raise ValueError("Vocabulary quiz session is not in progress.")

    stored_items = get_vocabulary_quiz_items(submission.session_id)
    expected_word_ids = {item["word_id"] for item in stored_items}
    submitted_word_ids = [answer.word_id for answer in submission.answers]
    if not submitted_word_ids:
        raise ValueError("Quiz answers must not be empty.")
    if len(submitted_word_ids) != len(set(submitted_word_ids)):
        raise ValueError("Each quiz word may be answered only once.")
    if set(submitted_word_ids) != expected_word_ids:
        raise ValueError("Quiz answers must match all assigned words.")

    answers_by_word_id = {answer.word_id: answer for answer in submission.answers}
    results: list[VocabularyQuizResultResponse] = []
    attempts: list[dict[str, object]] = []
    answered_at = datetime.now(timezone.utc).isoformat()
    for item in stored_items:
        answer: VocabularyQuizAnswerSubmission = answers_by_word_id[item["word_id"]]
        is_correct = answer.selected_meaning == item["correct_meaning"]
        word = (item.get("vocabulary_words") or {}).get("word")
        if not isinstance(word, str):
            raise RuntimeError("Vocabulary quiz item is missing its word.")

        results.append(
            VocabularyQuizResultResponse(
                word_id=item["word_id"],
                word=word,
                selected_meaning=answer.selected_meaning,
                correct_meaning=item["correct_meaning"],
                is_correct=is_correct,
            )
        )
        attempts.append(
            {
                "session_id": submission.session_id,
                "word_id": item["word_id"],
                "selected_meaning": answer.selected_meaning,
                "is_correct": is_correct,
                "answered_at": answered_at,
            }
        )

    create_vocabulary_quiz_attempts(submission.session_id, attempts)
    complete_vocabulary_quiz_session(submission.session_id)
    correct_count = sum(result.is_correct for result in results)
    total_count = len(results)
    return VocabularyQuizSubmitResponse(
        session_id=submission.session_id,
        total_count=total_count,
        correct_count=correct_count,
        accuracy=round(correct_count / total_count * 100, 2) if total_count else 0.0,
        results=results,
        status="completed",
    )
