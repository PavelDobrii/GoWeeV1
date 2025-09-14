"""API endpoints for workflow operations."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from src.common.db import get_session

from . import models, schemas

router = APIRouter()


@router.get("/workflows/{route_id}", response_model=schemas.WorkflowResponse)
async def get_workflow(route_id: str) -> schemas.WorkflowResponse:
    async with get_session() as session:
        workflow = await session.get(models.Workflow, route_id)
        if workflow is None:
            raise HTTPException(status_code=404, detail="workflow not found")
        result = await session.scalars(
            select(models.WorkflowStep).where(models.WorkflowStep.route_id == route_id)
        )
        steps = [
            schemas.WorkflowStepSchema(step=s.step, status=s.status, retries=s.retries)
            for s in result
        ]
    return schemas.WorkflowResponse(
        route_id=route_id,
        status=workflow.status,
        steps=steps,
    )


@router.post("/workflows/{route_id}/restart")
async def restart_workflow(route_id: str, step: str = Query(...)) -> dict[str, str]:
    if step != "tts_batch":
        raise HTTPException(status_code=400, detail="unsupported step")
    async with get_session() as session:
        result = await session.scalars(
            select(models.WorkflowStep).where(
                models.WorkflowStep.route_id == route_id,
                models.WorkflowStep.step.like("tts:%"),
            )
        )
        steps = list(result)
        if not steps:
            raise HTTPException(status_code=404, detail="steps not found")
        for s in steps:
            s.status = "pending"
            s.retries += 1
        await session.commit()
    return {"status": "ok"}
