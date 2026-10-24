from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from libs.events import subscribe
from services.chat import service

EVENT_TEXT = {
    "application.stage_changed": "Этап: {from} → {to}",
    "application.venue_changed": "Площадка изменена: {old_venue_id} → {new_venue_id}",
    "application.archived": "Заявка ушла в архив ({outcome})",
    "application.unarchived": "Заявка возвращена из архива",
    "application.closed_duplicate": "Заявка закрыта как дубль заявки {winner_id}",
    "invoice.issued": "Выставлен счёт {invoice_id} на {amount}",
    "invoice.cancelled": "Счёт {invoice_id} аннулирован ({reason})",
    "payment.linked": "Привязан платёж {amount} к счёту {invoice_id}",
    "booking.created": "Запись на {starts_at}",
    "booking.cancelled": "Запись на {starts_at} отменена ({reason})",
    "loan.overdue": "Срыв срока возврата книги {book_id}",
}


def _handler(template: str):
    async def handle(session: AsyncSession, payload: dict[str, Any]) -> None:
        await service.log_event(session, payload["application_id"], template.format(**payload))

    return handle


for _topic, _template in EVENT_TEXT.items():
    subscribe(_topic)(_handler(_template))
