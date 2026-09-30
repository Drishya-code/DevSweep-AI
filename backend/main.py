from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import structlog

from config import settings
from ai.factory import get_ai_provider, reset_ai_provider

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting DevSweep AI backend", version="0.1.0")
    logger.info("Configuration", demo_mode=settings.DEVSWEEP_DEMO_MODE, workspace_root=str(settings.workspace_root))

    # Initialize AI provider
    try:
        provider = get_ai_provider()
        logger.info("AI provider initialized", provider=provider.provider_name, model=provider.model_name)
    except Exception as e:
        logger.error("Failed to initialize AI provider", error=str(e))

    yield

    # Shutdown
    logger.info("Shutting down DevSweep AI backend")
    reset_ai_provider()


app = FastAPI(
    title="DevSweep AI",
    description="Clean your workspace. Keep your project. Restore it anytime.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    provider = get_ai_provider()
    return {
        "status": "healthy",
        "version": "0.1.0",
        "ai_provider": provider.provider_name,
        "ai_model": provider.model_name,
        "demo_mode": settings.DEVSWEEP_DEMO_MODE,
    }


@app.get("/api/config")
async def get_config():
    """Get non-sensitive configuration for frontend."""
    return {
        "demo_mode": settings.DEVSWEEP_DEMO_MODE,
        "default_risk_level": settings.DEVSWEEP_DEFAULT_RISK_LEVEL,
        "workspace_root": str(settings.workspace_root),
    }


# Import and include routers
from scanner.routes import router as scanner_router

app.include_router(scanner_router, prefix="/api/scan", tags=["scanner"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )