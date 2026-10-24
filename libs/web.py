from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from libs import db
from libs.errors import AccessDenied, DomainError, NotFound


async def session() -> AsyncIterator[AsyncSession]:
    async with db.sessionmaker().begin() as s:
        yield s


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFound)
    async def _not_found(_: Request, exc: NotFound) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(AccessDenied)
    async def _denied(_: Request, exc: AccessDenied) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=403)

    @app.exception_handler(DomainError)
    async def _domain(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(DBAPIError)
    async def _db(_: Request, exc: DBAPIError) -> JSONResponse:
        return JSONResponse({"detail": str(exc.orig)}, status_code=409)
