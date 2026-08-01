"""add server default for timestamp columns

Revision ID: 08261c197c69
Revises: ef88325b1a6f
Create Date: 2026-07-29 08:38:38.557418

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '08261c197c69'
down_revision: Union[str, Sequence[str], None] = 'ef88325b1a6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLES_WITH_TIMESTAMPS = ["matches", "news", "standings", "cards", "goals"]


def upgrade() -> None:
    """Upgrade schema."""
    # Migration ef88325b1a6f tạo created_at/updated_at là NOT NULL nhưng QUÊN
    # đặt server_default -> Postgres từ chối insert nếu code không tự set
    # giá trị (INSERT ... created_at bị null). Model Python đã khai báo
    # server_default=func.now() nhưng DB thật không có, nên phải vá ở DB.
    for table in TABLES_WITH_TIMESTAMPS:
        op.alter_column(table, "created_at", server_default=sa.text("now()"))
        op.alter_column(table, "updated_at", server_default=sa.text("now()"))


def downgrade() -> None:
    """Downgrade schema."""
    for table in TABLES_WITH_TIMESTAMPS:
        op.alter_column(table, "created_at", server_default=None)
        op.alter_column(table, "updated_at", server_default=None)
