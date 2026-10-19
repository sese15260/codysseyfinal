"""Persistence operations for learner profiles."""

from typing import TypedDict

from app.db.supabase import supabase


class Learner(TypedDict):
    id: str
    auth_user_id: str
    name: str
    age: int | None


def create_learner(
    *,
    auth_user_id: str,
    name: str,
    age: int,
) -> Learner:
    """Create a learner profile linked to an existing Supabase Auth user."""
    response = (
        supabase.table("learners")
        .insert(
            {
                "auth_user_id": auth_user_id,
                "name": name,
                "age": age,
            }
        )
        .execute()
    )

    if not response.data:
        raise RuntimeError("Learner insert did not return a row.")

    learner = response.data[0]
    if (
        learner.get("id") is None
        or learner.get("auth_user_id") is None
        or learner.get("name") is None
        or learner.get("age") is None
    ):
        raise RuntimeError("Learner insert returned incomplete data.")

    return learner


def get_learner_by_auth_user_id(auth_user_id: str) -> Learner | None:
    """Return the learner profile linked to one Supabase Auth user."""
    response = (
        supabase.table("learners")
        .select("id, auth_user_id, name, age")
        .eq("auth_user_id", auth_user_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    learner = response.data[0]
    if (
        learner.get("id") is None
        or learner.get("auth_user_id") is None
        or learner.get("name") is None
        or learner.get("age") is None
    ):
        raise RuntimeError("Learner query returned incomplete data.")

    return learner


def update_learner_profile(
    learner_id: str,
    *,
    name: str | None = None,
    age: int | None = None,
) -> Learner:
    """Update only supplied mutable profile fields and return the latest row."""
    profile_updates: dict[str, str | int] = {}
    if name is not None:
        profile_updates["name"] = name
    if age is not None:
        profile_updates["age"] = age

    if not profile_updates:
        raise ValueError("At least one profile field must be provided.")

    response = supabase.table("learners").update(profile_updates).eq("id", learner_id).execute()

    if not response.data:
        raise RuntimeError("Learner profile update did not return a row.")

    learner = response.data[0]
    if (
        learner.get("id") is None
        or learner.get("auth_user_id") is None
        or learner.get("name") is None
        or learner.get("age") is None
    ):
        raise RuntimeError("Learner profile update returned incomplete data.")

    return learner
