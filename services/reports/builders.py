"""Параметры и построение body запуска по типу отчёта.

Источники данных — только собственные таблицы сервиса: снимки метрик и журнал запусков.
"""

import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from libs.errors import DomainError
from services.reports import settings
from services.reports.models import MetricSnapshot, ReportDefinition, ReportRun

KINDS = ("metric_summary", "metric_trend", "run_audit")
METRIC_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)*$")

# Что можно переопределить при конкретном запуске, не меняя определение отчёта.
RUN_OVERRIDABLE = frozenset({"days", "as_of", "dimension"})
_ALLOWED = {
    "metric_summary": frozenset({"metrics", "days", "dimension", "as_of"}),
    "metric_trend": frozenset({"metric", "days", "dimension", "as_of"}),
    "run_audit": frozenset({"days", "as_of"}),
}

CENT = Decimal("0.01")


def _money(value: Decimal) -> str:
    return str(value.quantize(CENT))


def metric_name(value: Any) -> str:
    if not isinstance(value, str) or not METRIC_RE.match(value):
        raise DomainError(f"некорректное имя метрики: {value!r}")
    return value


def _days(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= settings.MAX_PERIOD_DAYS:
        raise DomainError(f"период отчёта — от 1 до {settings.MAX_PERIOD_DAYS} дней")
    return value


def _as_of(value: Any) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except TypeError, ValueError:
        raise DomainError(f"дата отчёта должна быть в формате ГГГГ-ММ-ДД: {value!r}") from None


def normalize_params(kind: str, params: dict[str, Any]) -> dict[str, Any]:
    """Проверяет параметры определения или запуска и приводит их к каноническому виду."""
    if kind not in KINDS:
        raise DomainError(f"неизвестный тип отчёта: {kind}")
    unknown = set(params) - _ALLOWED[kind]
    if unknown:
        raise DomainError(f"лишние параметры отчёта: {', '.join(sorted(unknown))}")
    out: dict[str, Any] = {}
    if "metrics" in params:
        metrics = params["metrics"]
        if not isinstance(metrics, list) or not metrics:
            raise DomainError("в сводном отчёте должна быть хотя бы одна метрика")
        if len(metrics) > settings.MAX_METRICS_PER_REPORT:
            raise DomainError(f"в сводном отчёте не больше {settings.MAX_METRICS_PER_REPORT} метрик")
        out["metrics"] = list(dict.fromkeys(metric_name(m) for m in metrics))
    if "metric" in params:
        out["metric"] = metric_name(params["metric"])
    if "days" in params:
        out["days"] = _days(params["days"])
    if "dimension" in params:
        if not isinstance(params["dimension"], str) or len(params["dimension"]) > 64:
            raise DomainError("разрез метрики — строка до 64 символов")
        out["dimension"] = params["dimension"]
    if "as_of" in params:
        out["as_of"] = _as_of(params["as_of"])
    return out


def require_complete(kind: str, params: dict[str, Any]) -> None:
    if kind == "metric_summary" and "metrics" not in params:
        raise DomainError("для сводного отчёта нужно указать метрики")
    if kind == "metric_trend" and "metric" not in params:
        raise DomainError("для отчёта-динамики нужно указать метрику")


def _period(params: dict[str, Any], default_day: date) -> tuple[date, date]:
    end = date.fromisoformat(params["as_of"]) if "as_of" in params else default_day
    days = params.get("days", settings.DEFAULT_PERIOD_DAYS)
    return end - timedelta(days=days - 1), end


async def _points(
    session: AsyncSession, metric: str, dimension: str, start: date, end: date
) -> list[MetricSnapshot]:
    rows = await session.scalars(
        select(MetricSnapshot)
        .where(
            MetricSnapshot.metric == metric,
            MetricSnapshot.dimension == dimension,
            MetricSnapshot.day.between(start, end),
        )
        .order_by(MetricSnapshot.day)
    )
    return list(rows.all())


async def _summary(session: AsyncSession, params: dict[str, Any], start: date, end: date) -> dict[str, Any]:
    dimension = params.get("dimension", "")
    metrics: dict[str, Any] = {}
    for metric in params["metrics"]:
        values = [p.value for p in await _points(session, metric, dimension, start, end)]
        if not values:
            metrics[metric] = {"points": 0}
            continue
        total = sum(values, Decimal(0))
        metrics[metric] = {
            "points": len(values),
            "total": _money(total),
            "avg": _money(total / len(values)),
            "min": _money(min(values)),
            "max": _money(max(values)),
        }
    if all(m["points"] == 0 for m in metrics.values()):
        raise DomainError("за период нет снимков ни по одной метрике отчёта")
    return {"dimension": dimension, "metrics": metrics}


async def _trend(session: AsyncSession, params: dict[str, Any], start: date, end: date) -> dict[str, Any]:
    metric, dimension = params["metric"], params.get("dimension", "")
    points = await _points(session, metric, dimension, start, end)
    if not points:
        raise DomainError(f"за период нет снимков метрики {metric}")
    return {
        "metric": metric,
        "dimension": dimension,
        "series": [{"day": p.day.isoformat(), "value": _money(p.value)} for p in points],
        "change": _money(points[-1].value - points[0].value),
    }


async def _audit(session: AsyncSession, run: ReportRun, start: date, end: date) -> dict[str, Any]:
    day = func.date(func.timezone("UTC", ReportRun.requested_at))
    in_period = (day.between(start, end), ReportRun.id != run.id)
    by_status = dict(
        (
            await session.execute(
                select(ReportRun.status, func.count()).where(*in_period).group_by(ReportRun.status)
            )
        ).all()
    )
    by_report = dict(
        (
            await session.execute(
                select(ReportDefinition.code, func.count())
                .join(ReportRun, ReportRun.definition_id == ReportDefinition.id)
                .where(*in_period)
                .group_by(ReportDefinition.code)
                .order_by(ReportDefinition.code)
            )
        ).all()
    )
    return {"total": sum(by_status.values()), "by_status": by_status, "by_report": by_report}


async def build(session: AsyncSession, definition: ReportDefinition, run: ReportRun) -> dict[str, Any]:
    params = {**definition.params, **run.params}
    anchor = run.scheduled_for or run.requested_at
    start, end = _period(params, anchor.date())
    match definition.kind:
        case "metric_summary":
            content = await _summary(session, params, start, end)
        case "metric_trend":
            content = await _trend(session, params, start, end)
        case "run_audit":
            content = await _audit(session, run, start, end)
        case other:
            raise DomainError(f"неизвестный тип отчёта: {other}")
    return {
        "kind": definition.kind,
        "code": definition.code,
        "title": definition.title,
        "period": {"from": start.isoformat(), "to": end.isoformat()},
        **content,
    }
