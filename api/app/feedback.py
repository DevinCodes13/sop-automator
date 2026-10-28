from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, or_, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .db import Base, get_db
from .models import User, now
from .security import require_role
from .sop_models import Sop, Workflow


class StepFeedback(Base):
    __tablename__ = "step_feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id"), index=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("runs.id"), nullable=True)
    step_number: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text)
    expected_needs_approval: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    expected_handler: Mapped[str | None] = mapped_column(String(30), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


router = APIRouter(prefix="/api", tags=["feedback"])
staff = require_role("admin", "instructor")


class FeedbackIn(BaseModel):
    run_id: int | None = None
    step_number: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=500)
    expected_needs_approval: bool | None = None
    expected_handler: Literal["manual", "record_client", "assign_student"] | None = None


@router.post("/workflows/{workflow_id}/feedback", status_code=201)
def give_feedback(workflow_id: int, body: FeedbackIn, db: Session = Depends(get_db), user: User = Depends(staff)):
    workflow = db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow not found")
    if body.step_number > len(workflow.steps):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "That step doesn't exist")
    fb = StepFeedback(workflow_id=workflow_id, user_id=user.id, **body.model_dump())
    db.add(fb)
    db.commit()
    return {"id": fb.id, "step": body.step_number, "action": workflow.steps[body.step_number - 1]["action"]}


@router.get("/feedback")
def list_feedback(db: Session = Depends(get_db), _: User = Depends(staff)):
    rows = db.scalars(select(StepFeedback).order_by(StepFeedback.id.desc()).limit(100)).all()
    out = []
    for fb in rows:
        workflow = db.get(Workflow, fb.workflow_id)
        out.append({
            "id": fb.id,
            "workflow_id": fb.workflow_id,
            "step": fb.step_number,
            "action": workflow.steps[fb.step_number - 1]["action"],
            "reason": fb.reason,
            "expected_needs_approval": fb.expected_needs_approval,
            "expected_handler": fb.expected_handler,
            "created_at": fb.created_at,
        })
    return out


@router.get("/evals/export")
def export_evals(db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    rows = db.scalars(
        select(StepFeedback)
        .where(or_(StepFeedback.expected_needs_approval.is_not(None), StepFeedback.expected_handler.is_not(None)))
        .order_by(StepFeedback.id)
    ).all()
    cases = []
    for fb in rows:
        workflow = db.get(Workflow, fb.workflow_id)
        sop = db.get(Sop, workflow.sop_id)
        step = workflow.steps[fb.step_number - 1]
        check = {"locate": step["source_quote"][:60]}
        if fb.expected_handler:
            check["handler"] = fb.expected_handler
        if fb.expected_needs_approval is not None:
            check["needs_approval"] = fb.expected_needs_approval
        cases.append({
            "name": f"feedback #{fb.id}: {fb.reason[:60]}",
            "sop_text": sop.raw_text,
            "step_checks": [check],
        })
    return cases
