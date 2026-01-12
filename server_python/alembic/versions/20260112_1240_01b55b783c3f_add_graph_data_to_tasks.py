"""add_graph_data_to_tasks

Revision ID: 01b55b783c3f
Revises: 001_initial
Create Date: 2026-01-12 12:40:36.877726

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '01b55b783c3f'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add graph_data column to tasks table
    op.add_column('tasks', sa.Column('graph_data', postgresql.JSON(), nullable=True))


def downgrade() -> None:
    # Remove graph_data column from tasks table
    op.drop_column('tasks', 'graph_data')
