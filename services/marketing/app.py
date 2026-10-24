from fastapi import FastAPI

from libs.web import install_error_handlers
from services import wiring
from services.marketing.api import router

wiring.load()
app = FastAPI(title="marketing")
app.include_router(router)
install_error_handlers(app)
