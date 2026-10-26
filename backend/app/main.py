"""
PricePilot — FastAPI Main Application Entry Point
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes.routes import router

app = FastAPI(
    title="PricePilot API",
    description=(
        "Event Revenue Optimizer — Backend mathematical engine for "
        "least-squares regression and Newton–Raphson revenue optimization."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv('PRICEPILOT_ALLOWED_ORIGINS',
        'http://localhost:5173,http://127.0.0.1:5173').split(','),
    allow_credentials=False,
    allow_methods=['GET', 'POST'],
    allow_headers=['Content-Type'],
)

app.include_router(router)


@app.exception_handler(RequestValidationError)
async def request_validation_error(request, exc):
    # Some JSON parsers accept NaN tokens. Never echo nonfinite raw inputs in an
    # error response: JSON serialization would fail and hide the useful 422.
    return JSONResponse(status_code=422, content={'detail': [
        {'loc': list(issue['loc']), 'msg': issue['msg'], 'type': issue['type']}
        for issue in exc.errors()
    ]})


@app.get("/")
async def root():
    return {
        "application": "PricePilot — Event Revenue Optimizer",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
