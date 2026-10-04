from contextlib import asynccontextmanager
import ipaddress
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import structlog

from config import settings
from ai.factory import get_ai_provider, reset_ai_provider
from persistence.database import persistence

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


def _is_loopback_listener(host: str) -> bool:
    if host.lower() == "testserver":
        return True  # Starlette's in-process test transport, not a network listener.
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host.lower() == "localhost"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting DevSweep AI backend", version="0.1.0")
    logger.info("Configuration", demo_mode=settings.DEVSWEEP_DEMO_MODE, workspace_root=str(settings.workspace_root))

    # Create or migrate the application history database before accepting requests.
    await persistence.initialize()

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
    await persistence.close()


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
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def reject_non_loopback_listener(request, call_next):
    # Also fail closed if a server runner bypasses BACKEND_HOST validation by
    # supplying its own wildcard/LAN --host argument.
    server = request.scope.get("server")
    if server and server[0] and not _is_loopback_listener(str(server[0])):
        return JSONResponse(
            status_code=403,
            content={"detail": "DevSweep AI accepts requests only through a loopback listener."},
        )
    return await call_next(request)


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
from cleanup.routes import router as cleanup_router
from ai.routes import router as ai_router
from security.routes import router as access_router

app.include_router(scanner_router, prefix="/api/scan", tags=["scanner"])
app.include_router(cleanup_router, prefix="/api/cleanup", tags=["cleanup"])
app.include_router(ai_router, prefix="/api/ai", tags=["ai"])
app.include_router(access_router, prefix="/api/access", tags=["access"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
