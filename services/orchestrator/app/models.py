"""Database models for workflow orchestration."""

from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from src.common.db import Base


class Workflow(Base):
    __tablename__ = "workflows"

    route_id = Column(String, primary_key=True)
    status = Column(String, nullable=False)

    steps = relationship(
        "WorkflowStep", back_populates="workflow", cascade="all, delete-orphan"
    )


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    __table_args__ = (UniqueConstraint("route_id", "step", name="uq_workflow_step"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    route_id = Column(
        String, ForeignKey("workflows.route_id"), index=True, nullable=False
    )
    step = Column(String, nullable=False)
    status = Column(String, nullable=False)
    retries = Column(Integer, nullable=False, default=0)

    workflow = relationship("Workflow", back_populates="steps")
