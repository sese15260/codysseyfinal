"""Authenticated endpoints for a learner's own account data."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth_dependencies import get_current_learner
from app.schemas.auth import CurrentLearnerResponse
from app.schemas.mypage import MyPageReportsResponse, ProfileUpdateRequest
from app.services.mypage_service import get_my_report_history, update_my_profile

router = APIRouter(prefix="/mypage", tags=["mypage"])


@router.get("/profile", response_model=CurrentLearnerResponse)
def read_my_profile(
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> CurrentLearnerResponse:
    """Return the profile already resolved from the caller's Bearer token."""
    return current_learner


@router.patch("/profile", response_model=CurrentLearnerResponse)
def update_my_profile_endpoint(
    submission: ProfileUpdateRequest,
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> CurrentLearnerResponse:
    """Update the caller's name and/or age without changing Auth account data."""
    try:
        learner = update_my_profile(current_learner.learner_id, submission)
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to update user profile.",
        ) from error

    return CurrentLearnerResponse(
        learner_id=str(learner["id"]),
        auth_user_id=str(learner["auth_user_id"]),
        name=learner["name"],
        age=learner["age"],
        email=current_learner.email,
    )


@router.get("/reports", response_model=MyPageReportsResponse)
def read_my_report_history(
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> MyPageReportsResponse:
    """Return completed diagnostic and learning reports owned by the caller."""
    try:
        return get_my_report_history(current_learner.learner_id)
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve report history.",
        ) from error
