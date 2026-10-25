import json
import logging

import anthropic
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .ai import PROMPT_VERSION, parse_sop
from .config import CLAUDE_MODEL
from .db import get_db
from .embeddings import chunk_text, embed_passages, embed_query
from .models import User
from .security import current_user, require_role
from .sop_models import Sop, SopChunk, Workflow

router = APIRouter(prefix="/api/sops", tags=["sops"])
log = logging.getLogger("sop.ai")
MAX_BYTES = 100_000
editors = require_role("admin", "instructor")


def get_sop_or_404(db: Session, sop_id: int) -> Sop:
    sop = db.get(Sop, sop_id)
    if not sop:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "SOP not found")
    return sop


@router.post("", status_code=201)
def upload_sop(
    title: str = Form(min_length=1, max_length=200),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(editors),
):
    data = file.file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too big (100 KB max)")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Upload a plain text or markdown file")
    if not text.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "File is empty")

    sop = Sop(title=title, raw_text=text, created_by=user.id)
    db.add(sop)
    db.flush()
    chunks = chunk_text(text)
    for i, (chunk, vector) in enumerate(zip(chunks, embed_passages(chunks))):
        db.add(SopChunk(sop_id=sop.id, chunk_index=i, text=chunk, embedding=vector))
    db.commit()
    return {"id": sop.id, "title": sop.title, "chunks": len(chunks)}


@router.post("/{sop_id}/parse")
def parse(sop_id: int, db: Session = Depends(get_db), user: User = Depends(editors)):
    sop = get_sop_or_404(db, sop_id)
    try:
        result, usage = parse_sop(sop.raw_text)
    except ValidationError as e:
        log.warning(json.dumps({"event": "ai_output_rejected", "sop_id": sop_id, "errors": e.error_count()}))
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "The AI's answer didn't pass our checks, so it was not saved")
    except ValueError:
        log.warning(json.dumps({"event": "ai_no_workflow", "sop_id": sop_id}))
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "The AI didn't return a workflow")
    except anthropic.APIError:
        log.exception("Claude API call failed")
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "The AI service had a problem. Try again.")

    if not result.is_procedure:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"This doesn't look like a procedure: {result.reason}")

    version = (db.scalar(select(func.max(Workflow.version)).where(Workflow.sop_id == sop_id)) or 0) + 1
    workflow = Workflow(
        sop_id=sop_id,
        version=version,
        prompt_version=PROMPT_VERSION,
        model=CLAUDE_MODEL,
        steps=[s.model_dump() for s in result.steps],
        created_by=user.id,
        **usage,
    )
    db.add(workflow)
    db.commit()
    log.info(json.dumps({"event": "workflow_parsed", "sop_id": sop_id, "version": version, **usage}))
    return {
        "workflow_id": workflow.id,
        "version": version,
        "prompt_version": PROMPT_VERSION,
        "model": CLAUDE_MODEL,
        "usage": usage,
        "steps": workflow.steps,
    }


@router.get("/{sop_id}/search")
def search(
    sop_id: int,
    q: str = Query(min_length=2, max_length=200),
    db: Session = Depends(get_db),
    _: User = Depends(current_user),
):
    get_sop_or_404(db, sop_id)
    distance = SopChunk.embedding.cosine_distance(embed_query(q)).label("distance")
    rows = db.execute(
        select(SopChunk.chunk_index, SopChunk.text, distance)
        .where(SopChunk.sop_id == sop_id)
        .order_by(distance)
        .limit(3)
    ).all()
    return [{"chunk": r.chunk_index, "text": r.text, "match": round(1 - r.distance, 3)} for r in rows]


@router.get("/{sop_id}/workflows")
def list_workflows(sop_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    get_sop_or_404(db, sop_id)
    rows = db.scalars(select(Workflow).where(Workflow.sop_id == sop_id).order_by(Workflow.version)).all()
    return [
        {
            "workflow_id": w.id,
            "version": w.version,
            "prompt_version": w.prompt_version,
            "model": w.model,
            "steps": len(w.steps),
            "created_at": w.created_at,
        }
        for w in rows
    ]


@router.get("")
def list_sops(db: Session = Depends(get_db), _: User = Depends(current_user)):
    out = []
    for sop in db.scalars(select(Sop).order_by(Sop.id)).all():
        latest = db.scalars(
            select(Workflow).where(Workflow.sop_id == sop.id).order_by(Workflow.version.desc()).limit(1)
        ).first()
        out.append({
            "id": sop.id,
            "title": sop.title,
            "latest_workflow_id": latest.id if latest else None,
            "latest_version": latest.version if latest else None,
            "prompt_version": latest.prompt_version if latest else None,
        })
    return out
