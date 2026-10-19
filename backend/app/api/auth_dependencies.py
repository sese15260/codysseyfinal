"""Reusable Bearer-token dependencies for authenticated auth endpoints."""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import SUPABASE_SECRET_KEY, SUPABASE_URL
from app.repositories.learner_repository import get_learner_by_auth_user_id
from app.schemas.auth import CurrentLearnerResponse
from supabase import create_client

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_learner(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentLearnerResponse:
    """Validate a Bearer token and return its linked learner profile.

    The token is verified with a request-scoped client so the shared admin/DB
    client never receives a user session or altered Authorization state.
    """
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not credentials.credentials.strip()
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token.",
        )

    auth_client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)
    try:
        auth_response = auth_client.auth.get_user(credentials.credentials)
    except Exception as error:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token.",
        ) from error

    auth_user = getattr(auth_response, "user", None)
    auth_user_id = getattr(auth_user, "id", None)
    email = getattr(auth_user, "email", None)
    if auth_user is None or auth_user_id is None or not email:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token.",
        )

    auth_user_id = str(auth_user_id)
    try:
        learner = get_learner_by_auth_user_id(auth_user_id)
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to load user profile.",
        ) from error

    if learner is None:
        raise HTTPException(
            status_code=500,
            detail="Unable to load user profile.",
        )

    return CurrentLearnerResponse(
        learner_id=str(learner["id"]),
        auth_user_id=auth_user_id,
        name=learner["name"],
        age=learner["age"],
        email=email,
    )
