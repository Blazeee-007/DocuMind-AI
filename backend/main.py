"""
FastAPI application entry point.
Registers all routers, configures CORS, rate limiting, and startup/shutdown hooks.
"""
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

load_dotenv()

from backend.routers import upload, analyze, chat
from backend.services.storage_service import start_cleanup_task, stop_cleanup_task

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)


# ---------------------------------------------------------------------------
# App lifespan (replaces deprecated on_event)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    start_cleanup_task()
    yield
    stop_cleanup_task()


# ---------------------------------------------------------------------------
# FastAPI instance
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Document & File Analyzer AI",
    description=(
        "Upload documents (PDF, DOCX, TXT, CSV) and get AI-powered "
        "summaries, data extraction, and document Q&A powered by an advanced AI."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------------------------------------------------------------------
# CORS — allow frontend origins
# ---------------------------------------------------------------------------
raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
origins = [o.strip() for o in raw_origins.split(",")]
# Also allow null origin so opening index.html from the filesystem works
origins.append("null")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Global error handler
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc), "status_code": 500},
    )

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(upload.router)
app.include_router(analyze.router)
app.include_router(chat.router)

# ---------------------------------------------------------------------------
# Serve frontend static files (when running via uvicorn, not docker-nginx)
# ---------------------------------------------------------------------------
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


# ---------------------------------------------------------------------------
# Health check (for Docker / load balancers)
# ---------------------------------------------------------------------------
@app.get("/health", tags=["Meta"])
async def health():
    return {"status": "ok", "version": "1.0.0"}
