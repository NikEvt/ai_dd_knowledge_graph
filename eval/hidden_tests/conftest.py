import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine

from libs import clock, db, settings
from services import wiring
import support as factories

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ("applications", "billing", "scheduling", "notifications", "chat", "events")


async def _drop_schemas() -> None:
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        rows = await conn.exec_driver_sql(
            "SELECT nspname FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' "
            "AND nspname NOT IN ('public', 'information_schema')"
        )
        for (schema,) in rows.fetchall():
            await conn.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
        await conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def migrated_db() -> None:
    asyncio.run(_drop_schemas())
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    command.upgrade(cfg, "head")
    wiring.load()


@pytest.fixture(autouse=True)
async def world(migrated_db: None):
    clock.freeze(factories.T0)
    await factories.truncate_all()
    await factories.seed()
    yield
    clock.freeze(None)
    await db.dispose()
