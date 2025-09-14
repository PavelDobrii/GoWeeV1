"""Pydantic schemas for API responses."""

from __future__ import annotations

from pydantic import BaseModel


class WorkflowStepSchema(BaseModel):
    step: str
    status: str
    retries: int


class WorkflowResponse(BaseModel):
    route_id: str
    status: str
    steps: list[WorkflowStepSchema]
