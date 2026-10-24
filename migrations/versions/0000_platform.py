"""platform services schemas (migrations/noise/*.sql)

Revision ID: 0000
Revises:
"""

from pathlib import Path

from alembic import op

revision = "0000"
down_revision = None
branch_labels = None
depends_on = None

SQL_DIR = Path(__file__).resolve().parents[1] / "noise"


def _statements(sql: str):
    """asyncpg не выполняет несколько команд за раз: режем по `;`, не трогая тела функций."""
    buf: list[str] = []
    inside_body = False
    for line in sql.splitlines():
        if not inside_body and line.lstrip().startswith("--"):
            continue
        buf.append(line)
        if line.count("$$") % 2:
            inside_body = not inside_body
        if not inside_body and line.rstrip().endswith(";"):
            yield "\n".join(buf)
            buf = []



def upgrade() -> None:
    bind = op.get_bind()
    for path in sorted(SQL_DIR.glob("*.sql")):
        for statement in _statements(path.read_text(encoding="utf-8")):
            bind.exec_driver_sql(statement)


def downgrade() -> None:
    pass
