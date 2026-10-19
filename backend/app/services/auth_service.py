"""Email signup workflow backed by Supabase Auth and learner profiles."""

from app.core.config import SUPABASE_SECRET_KEY, SUPABASE_URL
from app.db.supabase import supabase
from app.repositories.learner_repository import (
    create_learner,
    get_learner_by_auth_user_id,
)
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    SignupRequest,
    SignupResponse,
)
from supabase import create_client


class EmailAlreadyRegisteredError(ValueError):
    """Raised when Supabase Auth indicates that an email already has an account."""


class SignupServiceError(RuntimeError):
    """Raised when signup cannot complete because of server-side state or failure."""


class InvalidCredentialsError(ValueError):
    """Raised for login failures that must not reveal account existence."""


class LoginServiceError(RuntimeError):
    """Raised when login cannot complete because of server-side state or failure."""


def signup(submission: SignupRequest) -> SignupResponse:
    """Create a confirmed Auth user, then its linked learner profile.

    The admin API keeps the shared server client authenticated with its secret
    key. Password data is passed only to Supabase Auth and is never persisted
    in the public learner profile. If profile creation fails, the newly created
    Auth user is deleted with the server-side admin API before failure is raised.
    """
    try:
        auth_response = supabase.auth.admin.create_user(
            {
                "email": submission.email,
                "password": submission.password,
                "email_confirm": True,
            }
        )
    except Exception as error:
        if _is_duplicate_email_error(error):
            raise EmailAlreadyRegisteredError(
                "An account already exists for this email."
            ) from error
        raise SignupServiceError("Unable to create the authentication account.") from error

    auth_user = getattr(auth_response, "user", None)
    auth_user_id = getattr(auth_user, "id", None)
    if auth_user is None or auth_user_id is None:
        raise SignupServiceError("Authentication user creation did not return a user.")

    auth_user_id = str(auth_user_id)

    try:
        learner = create_learner(
            auth_user_id=auth_user_id,
            name=submission.name,
            age=submission.age,
        )
    except Exception as learner_error:
        _rollback_auth_user(auth_user_id, learner_error)

    return SignupResponse(
        learner_id=str(learner["id"]),
        auth_user_id=auth_user_id,
        name=learner["name"],
        age=learner["age"],
        email=submission.email,
    )


def login(submission: LoginRequest) -> LoginResponse:
    """Authenticate with an isolated client, then load the learner profile.

    ``sign_in_with_password`` stores the returned user session on its client.
    Creating that client per request prevents the shared server/admin client
    from being changed to a user's Authorization state.
    """
    auth_client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

    try:
        auth_response = auth_client.auth.sign_in_with_password(
            {
                "email": submission.email,
                "password": submission.password,
            }
        )
    except Exception as error:
        if _is_invalid_credentials_error(error):
            raise InvalidCredentialsError("Invalid email or password.") from error
        raise LoginServiceError("Unable to authenticate user.") from error

    session = getattr(auth_response, "session", None)
    auth_user = getattr(auth_response, "user", None) or getattr(session, "user", None)
    auth_user_id = getattr(auth_user, "id", None)
    access_token = getattr(session, "access_token", None)
    refresh_token = getattr(session, "refresh_token", None)

    if auth_user is None or auth_user_id is None or access_token is None or refresh_token is None:
        raise LoginServiceError("Authentication login returned incomplete data.")

    auth_user_id = str(auth_user_id)
    try:
        learner = get_learner_by_auth_user_id(auth_user_id)
    except Exception as error:
        raise LoginServiceError("Unable to load learner profile.") from error

    if learner is None:
        raise LoginServiceError("Authenticated user has no learner profile.")

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        learner_id=str(learner["id"]),
        auth_user_id=auth_user_id,
        name=learner["name"],
        age=learner["age"],
        email=submission.email,
    )


def _rollback_auth_user(auth_user_id: str, learner_error: Exception) -> None:
    """Remove a just-created Auth user when its learner profile cannot be saved."""
    try:
        supabase.auth.admin.delete_user(auth_user_id)
    except Exception as rollback_error:
        raise SignupServiceError(
            "Unable to create the learner profile or roll back the authentication account."
        ) from rollback_error

    raise SignupServiceError("Unable to create the learner profile.") from learner_error


def _is_duplicate_email_error(error: Exception) -> bool:
    """Classify known duplicate-email Auth responses without exposing them."""
    message = str(error).lower()
    return any(
        marker in message
        for marker in (
            "already registered",
            "already been registered",
            "already exists",
            "email exists",
        )
    )


def _is_invalid_credentials_error(error: Exception) -> bool:
    """Classify only credential failures that should receive the same 401."""
    message = str(error).lower()
    return any(
        marker in message
        for marker in (
            "invalid login credentials",
            "invalid credentials",
            "invalid email or password",
        )
    )
