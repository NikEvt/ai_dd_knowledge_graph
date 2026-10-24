from fastapi import FastAPI

from libs.web import install_error_handlers
from services import wiring
from services.chat.api import router

wiring.load()
app = FastAPI(title="chat")
app.include_router(router)
install_error_handlers(app)
