"""Endpoints for the free diagnostic."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth_dependencies import get_current_learner
from app.repositories.diagnostic_repository import get_diagnostic_session_owner
from app.schemas.auth import CurrentLearnerResponse
from app.schemas.diagnostic import (
    DiagnosticItemsResponse,
    DiagnosticReportResponse,
    DiagnosticSubmitRequest,
    DiagnosticSubmitResponse,
)
from app.services.diagnostic_report_service import get_diagnostic_report
from app.services.diagnostic_service import get_diagnostic_items, submit_diagnostic

router = APIRouter(prefix="/diagnostic", tags=["diagnostic"])


@router.get("/items", response_model=DiagnosticItemsResponse)
def read_diagnostic_items(
    limit: int = Query(default=20, ge=1),
) -> DiagnosticItemsResponse:
    """Return randomly selected public diagnostic items."""
    items = get_diagnostic_items(limit=limit)

    return DiagnosticItemsResponse(items=items, count=len(items))


@router.post("/submit", response_model=DiagnosticSubmitResponse)
def submit_diagnostic_answers(
    submission: DiagnosticSubmitRequest,
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> DiagnosticSubmitResponse:
    """Grade and persist a diagnostic submission for the authenticated learner."""
    try:
        return submit_diagnostic(
            submission=submission,
            learner_id=current_learner.learner_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to submit diagnostic.",
        ) from error


@router.get("/{session_id}/report", response_model=DiagnosticReportResponse)
def read_diagnostic_report(
    session_id: str,
    current_learner: CurrentLearnerResponse = Depends(get_current_learner),
) -> DiagnosticReportResponse:
    """Return the calculated report for one completed diagnostic session."""
    try:
        UUID(session_id)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail="session_id must be a valid UUID.",
        ) from error

    try:
        session = get_diagnostic_session_owner(session_id)
        if session is None or session["learner_id"] != current_learner.learner_id:
            raise HTTPException(status_code=404, detail="Diagnostic session not found.")

        report = get_diagnostic_report(session_id)

        if report["total_count"] == 0:
            raise HTTPException(
                status_code=404,
                detail="No attempts found for this diagnostic session.",
            )

        return DiagnosticReportResponse(
            diagnostic_session_id=session_id,
            **report,
        )
    except HTTPException:
        raise
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve diagnostic report.",
        ) from error
