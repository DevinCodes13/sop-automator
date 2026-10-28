from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from .db import get_db
from .models import User, now
from .run_models import Run, RunEvent, Service, StudentCheckin
from .runner import add_event, advance, school_today
from .metrics import RUNS_FINISHED
from .security import require_role
from .sop_models import Workflow

router = APIRouter(prefix="/api", tags=["runs"])
staff = require_role("admin", "instructor")


class RunCreate(BaseModel):
    workflow_id: int
    client_name: str = Field(min_length=1, max_length=200)
    cuts: int = Field(ge=1, le=5)
    payment: Literal["cash", "card"]
    simulate_fhir_failures: int = Field(default=0, ge=0, le=3)


def run_out(db: Session, run: Run) -> dict:
    events = db.scalars(select(RunEvent).where(RunEvent.run_id == run.id).order_by(RunEvent.id)).all()
    return {
        "id": run.id,
        "public_id": run.public_id,
        "workflow_id": run.workflow_id,
        "status": run.status,
        "current_step": run.current_step,
        "input": run.input,
        "context": run.context,
        "created_at": run.created_at,
        "events": [
            {"step": e.step, "event": e.event, "detail": e.detail, "user_id": e.user_id, "at": e.created_at}
            for e in events
        ],
    }


def locked_run(db: Session, run_id: int) -> Run:
    run = db.get(Run, run_id, with_for_update=True)
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    return run


@router.post("/checkins/me", status_code=201)
def check_in(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    today = school_today()
    existing = db.scalar(select(StudentCheckin).where(StudentCheckin.user_id == user.id, StudentCheckin.day == today))
    if existing:
        return {"student": user.email, "day": today, "already_checked_in": True}
    db.add(StudentCheckin(user_id=user.id, day=today, checked_in_at=now()))
    db.commit()
    return {"student": user.email, "day": today, "already_checked_in": False}


@router.get("/checkins/today")
def checkins_today(db: Session = Depends(get_db), _: User = Depends(staff)):
    today = school_today()
    clients = func.count(Service.id).label("clients")
    rows = db.execute(
        select(User.email, StudentCheckin.checked_in_at, clients)
        .join(User, User.id == StudentCheckin.user_id)
        .outerjoin(Service, and_(Service.student_id == StudentCheckin.user_id, Service.day == today))
        .where(StudentCheckin.day == today)
        .group_by(User.email, StudentCheckin.checked_in_at)
        .order_by(StudentCheckin.checked_in_at)
    ).all()
    return [{"student": r.email, "checked_in_at": r.checked_in_at, "clients_today": r.clients} for r in rows]


@router.post("/runs", status_code=201)
def start_run(body: RunCreate, db: Session = Depends(get_db), user: User = Depends(staff)):
    workflow = db.get(Workflow, body.workflow_id)
    if not workflow:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow not found")
    run = Run(
        workflow_id=workflow.id,
        status="running",
        current_step=1,
        input=body.model_dump(exclude={"workflow_id"}),
        context={},
        created_by=user.id,
    )
    db.add(run)
    db.flush()
    add_event(db, run, "run_started", None, {"workflow_version": workflow.version}, user.id)
    advance(db, run, user.id)
    return run_out(db, run)


@router.get("/runs")
def list_runs(db: Session = Depends(get_db), _: User = Depends(staff)):
    runs = db.scalars(select(Run).order_by(Run.id.desc()).limit(50)).all()
    return [
        {"id": r.id, "status": r.status, "current_step": r.current_step,
         "client_name": r.input.get("client_name"), "created_at": r.created_at}
        for r in runs
    ]


@router.get("/runs/{run_id}")
def get_run(run_id: int, db: Session = Depends(get_db), _: User = Depends(staff)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    return run_out(db, run)


@router.post("/runs/{run_id}/approve")
def approve(run_id: int, db: Session = Depends(get_db), user: User = Depends(staff)):
    run = locked_run(db, run_id)
    if run.status != "waiting_approval":
        raise HTTPException(status.HTTP_409_CONFLICT, "This run isn't waiting for approval")
    run.approved_step = run.current_step
    run.status = "running"
    add_event(db, run, "approved", run.current_step, {}, user.id)
    advance(db, run, user.id)
    return run_out(db, run)


@router.post("/runs/{run_id}/retry")
def retry(run_id: int, from_start: bool = False, db: Session = Depends(get_db), user: User = Depends(staff)):
    run = locked_run(db, run_id)
    if run.status not in ("failed", "completed"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Only failed or completed runs can be retried")
    if run.status == "completed" and not from_start:
        raise HTTPException(status.HTTP_409_CONFLICT, "Run already completed. Use from_start=true to re-run it.")
    if from_start:
        run.current_step = 1
    run.approved_step = None
    run.status = "running"
    add_event(db, run, "retry", run.current_step, {"from_start": from_start}, user.id)
    advance(db, run, user.id)
    return run_out(db, run)


@router.post("/runs/{run_id}/cancel")
def cancel(run_id: int, db: Session = Depends(get_db), user: User = Depends(staff)):
    run = locked_run(db, run_id)
    if run.status in ("completed", "cancelled"):
        raise HTTPException(status.HTTP_409_CONFLICT, "This run is already finished")
    run.status = "cancelled"
    RUNS_FINISHED.labels("cancelled").inc()
    add_event(db, run, "cancelled", run.current_step, {}, user.id)
    db.commit()
    return run_out(db, run)
