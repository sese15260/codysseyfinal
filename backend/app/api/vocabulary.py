"""Authenticated endpoints for a learner's vocabulary."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth_dependencies import get_current_learner
from app.schemas.auth import CurrentLearnerResponse
from app.schemas.vocabulary import (
    SavedWordsResponse,
    TodayWordsResponse,
    VocabularyQuizItemsResponse,
    VocabularyQuizStartResponse,
    VocabularyQuizSubmitRequest,
    VocabularyQuizSubmitResponse,
    WordMemorizedStatusRequest,
    WordSavedStatusRequest,
    WordStateResponse,
)
from app.services.vocabulary_quiz_service import (
    NoSavedWordsError,
    VocabularyQuizNotFoundError,
    get_vocabulary_quiz_items_for_learner,
    start_vocabulary_quiz,
    submit_vocabulary_quiz,
)
from app.services.vocabulary_service import (
    WordNotFoundError,
    get_saved_words,
    get_today_words,
    set_memorized_status,
    set_saved_status,
)

router = APIRouter(prefix="/words", tags=["vocabulary"])


@router.get("/today", response_model=TodayWordsResponse)
def read_today_words(
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> TodayWordsResponse:
    """Return the current learner's daily vocabulary in Korea Standard Time."""
    try:
        return get_today_words(current_learner.learner_id)
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve today's words.",
        ) from error


@router.get("/saved", response_model=SavedWordsResponse)
def read_saved_words(
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> SavedWordsResponse:
    """Return all saved words for the authenticated learner."""
    try:
        return get_saved_words(current_learner.learner_id)
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve saved words.",
        ) from error


@router.post("/quiz/start", response_model=VocabularyQuizStartResponse)
def start_saved_word_quiz(
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> VocabularyQuizStartResponse:
    """Create a fixed quiz from up to ten words saved by the current learner."""
    try:
        return start_vocabulary_quiz(current_learner.learner_id)
    except NoSavedWordsError as error:
        raise HTTPException(status_code=400, detail="No saved words available for quiz.") from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to start vocabulary quiz.",
        ) from error


@router.get("/quiz/{session_id}/items", response_model=VocabularyQuizItemsResponse)
def read_vocabulary_quiz_items(
    session_id: str,
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> VocabularyQuizItemsResponse:
    """Return fixed public items for a vocabulary quiz owned by the caller."""
    try:
        UUID(session_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="session_id must be a valid UUID.") from error

    try:
        return get_vocabulary_quiz_items_for_learner(
            session_id,
            current_learner.learner_id,
        )
    except VocabularyQuizNotFoundError as error:
        raise HTTPException(status_code=404, detail="Vocabulary quiz session not found.") from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve vocabulary quiz items.",
        ) from error


@router.post("/quiz/submit", response_model=VocabularyQuizSubmitResponse)
def submit_saved_word_quiz(
    submission: VocabularyQuizSubmitRequest,
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> VocabularyQuizSubmitResponse:
    """Grade and complete a fixed vocabulary quiz owned by the caller."""
    try:
        UUID(submission.session_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="session_id must be a valid UUID.") from error

    try:
        return submit_vocabulary_quiz(submission, current_learner.learner_id)
    except VocabularyQuizNotFoundError as error:
        raise HTTPException(status_code=404, detail="Vocabulary quiz session not found.") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to submit vocabulary quiz.",
        ) from error


@router.put("/{word_id}/saved", response_model=WordStateResponse)
def update_saved_status(
    word_id: str,
    submission: WordSavedStatusRequest,
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> WordStateResponse:
    """Set the current learner's saved state for one vocabulary word."""
    try:
        return set_saved_status(
            current_learner.learner_id,
            word_id,
            submission.is_saved,
        )
    except WordNotFoundError as error:
        raise HTTPException(status_code=404, detail="Word not found.") from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to update word state.",
        ) from error


@router.put("/{word_id}/memorized", response_model=WordStateResponse)
def update_memorized_status(
    word_id: str,
    submission: WordMemorizedStatusRequest,
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> WordStateResponse:
    """Set the current learner's memorized state for one vocabulary word."""
    try:
        return set_memorized_status(
            current_learner.learner_id,
            word_id,
            submission.is_memorized,
        )
    except WordNotFoundError as error:
        raise HTTPException(status_code=404, detail="Word not found.") from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to update word state.",
        ) from error
