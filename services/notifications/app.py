from fastapi import FastAPI

from libs.web import install_error_handlers
from services import wiring

wiring.load()
app = FastAPI(title="notifications")
install_error_handlers(app)
