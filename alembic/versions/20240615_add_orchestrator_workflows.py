"""add orchestrator workflow tables"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20240615_orchestrator"
down_revision = "20240605_init_auth_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflows",
        sa.Column("route_id", sa.String(), primary_key=True),
        sa.Column("status", sa.String(), nullable=False),
    )
    op.create_table(
        "workflow_steps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "route_id", sa.String(), sa.ForeignKey("workflows.route_id"), nullable=False
        ),
        sa.Column("step", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("retries", sa.Integer(), nullable=False, default=0),
    )
    op.create_index(
        "ix_workflow_steps_route_id", "workflow_steps", ["route_id"], unique=False
    )
    op.create_unique_constraint(
        "uq_workflow_step", "workflow_steps", ["route_id", "step"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_workflow_step", "workflow_steps", type_="unique")
    op.drop_index("ix_workflow_steps_route_id", table_name="workflow_steps")
    op.drop_table("workflow_steps")
    op.drop_table("workflows")
