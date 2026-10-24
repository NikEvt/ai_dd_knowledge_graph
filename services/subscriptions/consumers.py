from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from libs.events import subscribe
from services.subscriptions import service


@subscribe("subscriptions.created")
async def on_created(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.recheck_holder(session, payload["subscription_id"])


@subscribe("subscriptions.holder_updated")
async def on_holder_updated(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.recheck_holder(session, payload["subscription_id"])


@subscribe("subscriptions.holder_rejected")
async def on_holder_rejected(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.add_notice(
        session,
        payload["subscription_id"],
        "holder_rejected",
        f"Данные держателя не подтверждены: {payload['reason']}. Обновите их в личном кабинете.",
    )


@subscribe("subscriptions.invoice_issued")
async def on_invoice_issued(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.add_notice(
        session,
        payload["subscription_id"],
        "invoice",
        f"Выставлен счёт на {payload['amount']} ₽ за месяц с {payload['period_start']}.",
    )


@subscribe("subscriptions.payment_completed")
async def on_payment_completed(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.apply_payment(session, payload["subscription_id"], payload["invoice_id"])


@subscribe("subscriptions.activated")
async def on_activated(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.add_notice(
        session, payload["subscription_id"], "activated", f"Абонемент действует до {payload['paid_until']}."
    )


@subscribe("subscriptions.renewed")
async def on_renewed(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.add_notice(
        session, payload["subscription_id"], "renewed", f"Абонемент продлён до {payload['paid_until']}."
    )


@subscribe("subscriptions.closed_duplicate")
async def on_closed_duplicate(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.void_open_invoices(session, payload["subscription_id"])
    await service.add_notice(
        session,
        payload["subscription_id"],
        "closed_duplicate",
        f"Абонемент закрыт: у вас действует абонемент №{payload['kept_id']}.",
    )


@subscribe("subscriptions.grace_started")
async def on_grace_started(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.add_notice(
        session,
        payload["subscription_id"],
        "grace",
        f"Оплаченный месяц закончился. Абонемент действует до {payload['grace_until']}, оплатите продление.",
    )


@subscribe("subscriptions.expired")
async def on_expired(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.void_open_invoices(session, payload["subscription_id"])
    await service.add_notice(session, payload["subscription_id"], "expired", "Абонемент закрыт: не оплачен.")


@subscribe("subscriptions.refund_required")
async def on_refund_required(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.add_notice(
        session,
        payload["subscription_id"],
        "refund",
        f"Оплата {payload['amount']} ₽ по счёту №{payload['invoice_id']} будет возвращена.",
    )
