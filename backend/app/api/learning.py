"""Endpoints for weak-subtype practice learning."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth_dependencies import get_current_learner
from app.schemas.auth import CurrentLearnerResponse
from app.schemas.learning import (
    LearningRecommendationsResponse,
    LearningTestItemsResponse,
    LearningTestReportResponse,
    LearningTestStartRequest,
    LearningTestStartResponse,
    LearningTestSubmitRequest,
    LearningTestSubmitResponse,
    WeakLearningItemResponse,
    WeakLearningReportResponse,
    WeakLearningStartRequest,
    WeakLearningStartResponse,
    WeakLearningSubmitRequest,
    WeakLearningSubmitResponse,
    WrongReviewItemsResponse,
    WrongReviewReportResponse,
    WrongReviewStartResponse,
    WrongReviewSubmitRequest,
    WrongReviewSubmitResponse,
)
from app.services.learning_recommendation_service import get_learning_recommendations
from app.services.learning_test_report_service import get_learning_test_report
from app.services.learning_test_service import (
    get_learning_test_items,
    start_learning_test_session,
    submit_learning_test,
)
from app.services.weak_learning_report_service import get_weak_learning_report
from app.services.weak_learning_service import (
    get_weak_learning_item,
    start_weak_learning_session,
)
from app.services.weak_learning_service import (
    submit_weak_learning_answer as submit_weak_learning_answer_service,
)
from app.services.wrong_review_service import (
    get_wrong_review_items,
    get_wrong_review_report,
    start_wrong_review,
    submit_wrong_review,
)

router = APIRouter(prefix="/learning", tags=["learning"])


@router.get("/recommendations", response_model=LearningRecommendationsResponse)
def read_learning_recommendations(
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> LearningRecommendationsResponse:
    """Return deterministic long-term recommendations for the caller only."""
    try:
        return get_learning_recommendations(current_learner.learner_id)
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve learning recommendations.",
        ) from error


@router.post("/wrong/start", response_model=WrongReviewStartResponse)
def start_wrong_review_session(
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> WrongReviewStartResponse:
    """Create a fixed review session from the caller's unresolved wrong answers."""
    try:
        return start_wrong_review(current_learner.learner_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to start wrong review.",
        ) from error


@router.get("/wrong/{session_id}/items", response_model=WrongReviewItemsResponse)
def read_wrong_review_items(
    session_id: str,
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> WrongReviewItemsResponse:
    """Return fixed public items for one caller-owned wrong review session."""
    try:
        UUID(session_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="session_id must be a valid UUID.") from error

    try:
        return get_wrong_review_items(session_id, current_learner.learner_id)
    except ValueError as error:
        status_code = 404 if str(error) == "Wrong review session not found." else 400
        raise HTTPException(status_code=status_code, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve wrong review items.",
        ) from error


@router.post("/wrong/submit", response_model=WrongReviewSubmitResponse)
def submit_wrong_review_answers(
    submission: WrongReviewSubmitRequest,
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> WrongReviewSubmitResponse:
    """Grade and complete one caller-owned wrong review session."""
    try:
        UUID(submission.session_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="session_id must be a valid UUID.") from error

    try:
        return submit_wrong_review(submission, current_learner.learner_id)
    except ValueError as error:
        status_code = 404 if str(error) == "Wrong review session not found." else 400
        raise HTTPException(status_code=status_code, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to submit wrong review.",
        ) from error


@router.get("/wrong/{session_id}/report", response_model=WrongReviewReportResponse)
def read_wrong_review_report(
    session_id: str,
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> WrongReviewReportResponse:
    """Return summary data for a completed caller-owned wrong review session."""
    try:
        UUID(session_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="session_id must be a valid UUID.") from error

    try:
        return get_wrong_review_report(session_id, current_learner.learner_id)
    except ValueError as error:
        status_code = 404 if str(error) == "Wrong review session not found." else 400
        raise HTTPException(status_code=status_code, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve wrong review report.",
        ) from error


@router.post("/test/start", response_model=LearningTestStartResponse)
def start_learning_test(
    request: LearningTestStartRequest,
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> LearningTestStartResponse:
    """Start a general learning-test session for the current learner."""
    try:
        learning_session_id = start_learning_test_session(
            mode=request.mode,
            learner_id=current_learner.learner_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to start learning test session.",
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to start learning test session.",
        ) from error

    return LearningTestStartResponse(
        learning_session_id=learning_session_id,
        mode=request.mode,
        status="in_progress",
    )


@router.get(
    "/test/{learning_session_id}/items",
    response_model=LearningTestItemsResponse,
)
def read_learning_test_items(
    learning_session_id: str,
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> LearningTestItemsResponse:
    """Return 20 public practice items for an active learning-test session."""
    try:
        UUID(learning_session_id)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="learning_session_id must be a valid UUID.",
        ) from error

    try:
        return get_learning_test_items(
            learning_session_id,
            learner_id=current_learner.learner_id,
        )
    except ValueError as error:
        status_code = 404 if str(error) == "Learning test session not found." else 400
        raise HTTPException(status_code=status_code, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve learning test items.",
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve learning test items.",
        ) from error


@router.get(
    "/test/{learning_session_id}/report",
    response_model=LearningTestReportResponse,
)
def read_learning_test_report(
    learning_session_id: str,
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> LearningTestReportResponse:
    """Return the read-only report for one completed general learning test."""
    try:
        UUID(learning_session_id)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="learning_session_id must be a valid UUID.",
        ) from error

    try:
        return get_learning_test_report(
            learning_session_id,
            learner_id=current_learner.learner_id,
        )
    except ValueError as error:
        status_code = 404 if str(error) == "Learning test session not found." else 400
        raise HTTPException(status_code=status_code, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve learning test report.",
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve learning test report.",
        ) from error


@router.post("/test/submit", response_model=LearningTestSubmitResponse)
def submit_learning_test_answers(
    submission: LearningTestSubmitRequest,
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> LearningTestSubmitResponse:
    """Grade and store all assigned answers for one general learning test."""
    try:
        UUID(submission.learning_session_id)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="learning_session_id must be a valid UUID.",
        ) from error

    try:
        return submit_learning_test(
            submission,
            learner_id=current_learner.learner_id,
        )
    except ValueError as error:
        status_code = 404 if str(error) == "Learning test session not found." else 400
        raise HTTPException(status_code=status_code, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to submit learning test.",
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to submit learning test.",
        ) from error


@router.get("/weak/{subtype_id}/item", response_model=WeakLearningItemResponse)
def read_weak_learning_item(subtype_id: str) -> WeakLearningItemResponse:
    """Return one random public practice item for a weak subtype."""
    item = get_weak_learning_item(subtype_id)

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="No practice questions found for this subtype.",
        )

    return WeakLearningItemResponse(**item)


@router.get(
    "/weak/{learning_session_id}/report",
    response_model=WeakLearningReportResponse,
)
def read_weak_learning_report(
    learning_session_id: str,
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> WeakLearningReportResponse:
    """Return the report for a weak-learning session."""
    try:
        UUID(learning_session_id)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="learning_session_id must be a valid UUID.",
        ) from error

    try:
        return get_weak_learning_report(
            learning_session_id,
            learner_id=current_learner.learner_id,
        )
    except ValueError as error:
        status_code = (
            404
            if str(error)
            in {
                "Learning session not found.",
                "Learning session has no attempts.",
            }
            else 400
        )
        raise HTTPException(status_code=status_code, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve weak learning report.",
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve weak learning report.",
        ) from error


@router.post("/weak/submit", response_model=WeakLearningSubmitResponse)
def submit_weak_learning_answer(
    submission: WeakLearningSubmitRequest,
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> WeakLearningSubmitResponse:
    """Validate a session, grade one practice answer, and store its attempt."""
    try:
        UUID(submission.learning_session_id)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="learning_session_id must be a valid UUID.",
        ) from error

    try:
        return submit_weak_learning_answer_service(
            submission,
            learner_id=current_learner.learner_id,
        )
    except ValueError as error:
        status_code = 404 if str(error) == "Learning session not found." else 400
        raise HTTPException(status_code=status_code, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to grade weak learning answer.",
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to grade weak learning answer.",
        ) from error


@router.post("/weak/start", response_model=WeakLearningStartResponse)
def start_weak_learning(
    request: WeakLearningStartRequest,
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> WeakLearningStartResponse:
    """Start an in-progress weak-subtype session for the current learner."""
    try:
        learning_session_id = start_weak_learning_session(
            subtype_id=request.subtype_id,
            learner_id=current_learner.learner_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to start weak learning session.",
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to start weak learning session.",
        ) from error

    return WeakLearningStartResponse(
        learning_session_id=learning_session_id,
        subtype_id=request.subtype_id,
        status="in_progress",
    )
