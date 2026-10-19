"""Authenticated, retrieval-grounded AI explanation endpoint."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth_dependencies import get_current_learner
from app.clients.openai_client import AIProviderError
from app.schemas.ai import AIExplanationResponse
from app.schemas.auth import CurrentLearnerResponse
from app.services.ai_explanation_service import (
    ExplanationAttemptNotFoundError,
    get_ai_explanation,
)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/explanations/{attempt_id}", response_model=AIExplanationResponse)
def read_attempt_explanation(
    attempt_id: int,
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> AIExplanationResponse:
    """Generate or retrieve a cached explanation for the caller's attempt."""
    try:
        return get_ai_explanation(attempt_id, current_learner.learner_id)
    except ExplanationAttemptNotFoundError as error:
        raise HTTPException(status_code=404, detail="Question attempt not found.") from error
    except AIProviderError as error:
        raise HTTPException(
            status_code=502,
            detail="AI explanation is temporarily unavailable.",
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve AI explanation.",
        ) from error
