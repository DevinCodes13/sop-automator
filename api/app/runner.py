import json
import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from .config import SCHOOL_TZ
from .fhir import StepError, create_patient
from .run_models import Run, RunEvent, Service, StudentCheckin
from .sop_models import Workflow

log = logging.getLogger("sop.runner")


def school_today() -> date:
    return datetime.now(ZoneInfo(SCHOOL_TZ)).date()


def add_event(db: Session, run: Run, event: str, step=None, detail=None, user_id=None):
    detail = detail or {}
    db.add(RunEvent(run_id=run.id, step=step, event=event, detail=detail, user_id=user_id))
    log.info(json.dumps({"event": event, "run_id": run.id, "step": step, **detail}, default=str))


def do_manual(db: Session, run: Run, step: dict) -> dict:
    return {"note": "Done by a person"}


def do_record_client(db: Session, run: Run, step: dict) -> dict:
    simulate = 0 if run.context.get("simulation_used") else run.input.get("simulate_fhir_failures", 0)
    run.context = {**run.context, "simulation_used": True}
    result = create_patient(run.public_id, run.input["client_name"], simulate)
    run.context = {**run.context, "patient_id": result["patient_id"]}
    return result


def do_assign_student(db: Session, run: Run, step: dict) -> dict:
    existing = db.scalar(select(Service).where(Service.run_id == run.id))
    if existing:
        return {"student_id": existing.student_id, "reused": True}
    today = school_today()
    clients = func.count(Service.id).label("clients")
    row = db.execute(
        select(StudentCheckin.user_id, clients)
        .outerjoin(Service, and_(Service.student_id == StudentCheckin.user_id, Service.day == today))
        .where(StudentCheckin.day == today)
        .group_by(StudentCheckin.user_id, StudentCheckin.checked_in_at)
        .order_by(clients, StudentCheckin.checked_in_at)
        .limit(1)
    ).first()
    if not row:
        raise StepError("No students are checked in today")
    db.add(Service(
        run_id=run.id,
        student_id=row.user_id,
        day=today,
        client_name=run.input["client_name"],
        cuts=run.input["cuts"],
        payment=run.input["payment"],
        fhir_patient_id=run.context.get("patient_id"),
    ))
    run.context = {**run.context, "student_id": row.user_id}
    return {"student_id": row.user_id, "clients_before": row.clients}


HANDLERS = {
    "manual": do_manual,
    "record_client": do_record_client,
    "assign_student": do_assign_student,
}


def advance(db: Session, run: Run, user_id: int) -> Run:
    steps = db.get(Workflow, run.workflow_id).steps
    while run.current_step <= len(steps):
        n = run.current_step
        step = steps[n - 1]
        if step.get("needs_approval") and run.approved_step != n:
            run.status = "waiting_approval"
            add_event(db, run, "waiting_approval", n, {"action": step["action"]})
            db.commit()
            return run
        handler_name = step.get("handler", "manual")
        handler = HANDLERS.get(handler_name, do_manual)
        add_event(db, run, "step_started", n, {"action": step["action"], "handler": handler_name}, user_id)
        try:
            result = handler(db, run, step)
        except StepError as e:
            run.status = "failed"
            add_event(db, run, "step_failed", n, {"error": str(e)}, user_id)
            db.commit()
            return run
        add_event(db, run, "step_done", n, result, user_id)
        run.current_step = n + 1
        db.commit()
    run.status = "completed"
    add_event(db, run, "run_completed", None, {}, user_id)
    db.commit()
    return run
