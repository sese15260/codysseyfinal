"""Email authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth_dependencies import get_current_learner
from app.schemas.auth import (
    CurrentLearnerResponse,
    LoginRequest,
    LoginResponse,
    SignupRequest,
    SignupResponse,
)
from app.services.auth_service import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    LoginServiceError,
    SignupServiceError,
    login,
    signup,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=CurrentLearnerResponse)
def read_current_learner(
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> CurrentLearnerResponse:
    """Return the learner profile associated with the Bearer access token."""
    return current_learner


@router.post("/login", response_model=LoginResponse)
def login_with_email(submission: LoginRequest) -> LoginResponse:
    """Authenticate with an isolated Auth client and return learner data."""
    try:
        return login(submission)
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        ) from error
    except LoginServiceError as error:
        raise HTTPException(status_code=500, detail="Unable to complete login.") from error
    except Exception as error:
        raise HTTPException(status_code=500, detail="Unable to complete login.") from error


@router.post("/signup", response_model=SignupResponse, status_code=201)
def signup_with_email(submission: SignupRequest) -> SignupResponse:
    """Create a Supabase Auth account and its public learner profile."""
    try:
        return signup(submission)
    except EmailAlreadyRegisteredError as error:
        raise HTTPException(status_code=409, detail="Email is already registered.") from error
    except SignupServiceError as error:
        raise HTTPException(status_code=500, detail="Unable to create account.") from error
    except Exception as error:
        raise HTTPException(status_code=500, detail="Unable to create account.") from error
