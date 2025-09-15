"""Initial tables for auth_profile service"""

import sqlalchemy as sa

from alembic import op

revision = '20240605_init_auth_profile'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'),
    )
    op.create_table(
        'profiles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'user_id',
            sa.Integer(),
            sa.ForeignKey('users.id'),
            nullable=False,
            unique=True,
        ),
        sa.Column('first_name', sa.String(length=255)),
        sa.Column('last_name', sa.String(length=255)),
    )
    op.create_table(
        'consents',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'user_id',
            sa.Integer(),
            sa.ForeignKey('users.id'),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            'marketing',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
        sa.Column(
            'terms',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )

def downgrade() -> None:
    op.drop_table('consents')
    op.drop_table('profiles')
    op.drop_table('users')
