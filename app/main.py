from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from app.api import shorten, redirect, analytics
from app.core.config import settings
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    await init_db()
    yield


app = FastAPI(
    title="URL Shortener API",
    description="Production-grade URL shortening service with Redis caching and analytics",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(round(time.time() - start, 4))
    return response


@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


# Register routers
app.include_router(shorten.router, prefix="/api", tags=["urls"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])
app.include_router(redirect.router, tags=["redirect"])
