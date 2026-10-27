"""Мутации кода для проверки drift detection. Каждая — правка «как в PR», модель знаний не обновляется."""

import re
import sys
from pathlib import Path


def sub(path: str, old: str, new: str) -> None:
    p = Path(path)
    s = p.read_text()
    assert old in s, f"{path}: не найдено {old[:60]!r}"
    p.write_text(s.replace(old, new, 1))


def m0_noop() -> None:
    """Контроль: без изменений кода (проверка, что на чистой ветке CI зелёный)."""
    Path("NOTES.txt").write_text("контрольный PR без изменений кода\n")


def m1_logic_change() -> None:
    """Поведение правила меняется внутри функции: переплата больше не помечается."""
    sub("services/billing/service.py", "    if after > invoice.amount:\n        payment.overpayment = True\n",
        "    if after > invoice.amount * 2:\n        payment.overpayment = True\n")


def m2_helper_logic() -> None:
    """Логика меняется во вспомогательной функции; символ, на который ссылается правило, не тронут."""
    sub("services/applications/review.py", 'REQUIRED_CLIENT_FIELDS = ("full_name", "passport", "birth_date")',
        'REQUIRED_CLIENT_FIELDS = ("full_name", "passport", "birth_date")\nOPTIONAL_FIELDS = ("birth_date",)')
    sub("services/applications/review.py",
        "    return [f for f in REQUIRED_CLIENT_FIELDS if not getattr(client, f)]",
        "    return [f for f in REQUIRED_CLIENT_FIELDS"
        " if f not in OPTIONAL_FIELDS and not getattr(client, f)]")


def m3_new_check() -> None:
    """Новая миграция с CHECK, правила под неё нет."""
    Path("migrations/versions/0002_fine_amount_cap.py").write_text('''"""cap fine amount

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE billing.fines ADD CONSTRAINT fines_amount_cap CHECK (amount <= 100000)")


def downgrade() -> None:
    op.execute("ALTER TABLE billing.fines DROP CONSTRAINT fines_amount_cap")
''')


def m4_topic_rename() -> None:
    """Топик переименован у издателя, подписчики (billing, scheduling, chat) не обновлены."""
    sub("services/applications/dedup.py", '"application.closed_duplicate"', '"application.duplicate_closed"')


def m5_format_only() -> None:
    """Только форматирование и переименование локальной переменной — поведение не меняется."""
    sub("services/billing/service.py", "    before = await paid_amount(session, invoice_id)\n",
        "    paid_before = await paid_amount(session, invoice_id)\n")
    p = Path("services/billing/service.py")
    s = p.read_text()
    s = s.replace("    after = before + amount\n", "    after = paid_before + amount\n")
    s = s.replace("    if before < invoice.amount <= after:\n",
                  "    if paid_before < invoice.amount <= after:\n")
    p.write_text(s)


def m6_comments_only() -> None:
    """Только комментарии и docstring."""
    sub("services/scheduling/jobs.py",
        "async def flag_overdue(session: AsyncSession, now: datetime) -> list[int]:\n",
        "async def flag_overdue(session: AsyncSession, now: datetime) -> list[int]:\n"
        '    """Отмечает просроченные выдачи и публикует loan.overdue."""\n'
        "    # Срок считается от даты выдачи.\n")


MUTATIONS = {name.split("_", 1)[0].upper(): fn for name, fn in globals().items() if re.match(r"m\d_", name)}

if __name__ == "__main__":
    MUTATIONS[sys.argv[1]]()
