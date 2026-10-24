from sqlalchemy.ext.asyncio import AsyncSession

from libs.bpm import engine as bpm
from services.applications.models import Application
from services.billing import public as billing
from services.scheduling import public as scheduling


@bpm.guard("settled")
async def settled(session: AsyncSession, app: Application) -> bool:
    """Все книги возвращены или списаны, штрафы погашены."""
    open_loans = await scheduling.open_loans_count(session, app.id)
    open_fines = await billing.open_fines_count(session, app.id)
    return open_loans == 0 and open_fines == 0
