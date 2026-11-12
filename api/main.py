import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from api.errors import (
    ApiException,
    api_exception_handler,
    generic_exception_handler,
    validation_exception_handler,
    value_error_handler,
)
from api.routers import backtest, forecast, health, peak, procurement
from api.store import store
from src.common.config import load_config


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.load()
    yield


app = FastAPI(
    title="PeakWise API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_exception_handler(ApiException, api_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(ValueError, value_error_handler)
app.add_exception_handler(Exception, generic_exception_handler)

config = load_config()
cors_origins = list(config.get("api", {}).get("cors_origins", ["http://localhost:5173", "http://127.0.0.1:5173"]))
env_cors = os.getenv("CORS_ORIGINS")
if env_cors:
    cors_origins.extend([o.strip() for o in env_cors.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prefix = "/api/v1"
app.include_router(health.router, prefix=prefix)
app.include_router(forecast.router, prefix=prefix)
app.include_router(peak.router, prefix=prefix)
app.include_router(backtest.router, prefix=prefix)
app.include_router(procurement.router, prefix=prefix)
