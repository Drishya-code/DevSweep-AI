from contextlib import asynccontextmanager
import ipaddress
import time
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-DevSweep-Session"],
)


class HostedDemoBoundaryMiddleware:
    """Apply the route allowlist and a streaming body cap before route parsing."""
    def __init__(self, app):
        self.app = app
        self._limits = {}

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        server = scope.get("server")
        if server and server[0] and not _is_loopback_listener(str(server[0])) and not settings.DEVSWEEP_HOSTED_DEMO:
            await JSONResponse(status_code=403, content={"detail": "DevSweep AI accepts requests only through a loopback listener."})(scope, receive, send)
            return
        if settings.DEVSWEEP_HOSTED_DEMO:
            method = scope.get("method", "GET")
            path = scope.get("path", "/")
            allowed = {
                ("GET", "/health"), ("GET", "/api/config"),
                ("POST", "/api/demo/sessions"), ("GET", "/api/demo/workspace"),
                ("POST", "/api/demo/preview"), ("POST", "/api/demo/confirm"),
                ("POST", "/api/demo/reset"), ("POST", "/api/demo/analyze"),
                ("POST", "/api/ai/metadata"),
            }
            if method == "POST" and path.startswith("/api/demo/restore/"):
                allowed.add((method, path))
            preflight_paths = {"/api/demo/sessions", "/api/demo/workspace", "/api/demo/preview", "/api/demo/confirm", "/api/demo/reset", "/api/demo/analyze", "/api/ai/metadata", "/api/config"}
            frontend_asset = method == "GET" and (path in {"/", "/favicon.svg"} or path.startswith("/assets/"))
            if (method, path) not in allowed and not frontend_asset and not (method == "OPTIONS" and path in preflight_paths):
                await JSONResponse(status_code=404, content={"detail": "Endpoint unavailable in hosted demo mode."})(scope, receive, send)
                return

            # Small process-local fixed window limit. Use a shared gateway limit for
            # multi-replica production deployments as documented in DEPLOYMENT.md.
            if path in {"/api/demo/analyze", "/api/ai/metadata"} and method == "POST":
                now = time.monotonic()
                client = scope.get("client") or ("unknown", 0)
                key = (str(client[0]), path)
                start, count = self._limits.get(key, (now, 0))
                if now - start >= 60:
                    start, count = now, 0
                if count >= 8:
                    await JSONResponse(status_code=429, content={"detail": "AI request limit reached. Wait a minute and retry."})(scope, receive, send)
                    return
                self._limits[key] = (start, count + 1)

            chunks = []
            size = 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                size += len(chunk)
                if size > 32768:
                    await JSONResponse(status_code=413, content={"detail": "Request body is too large."})(scope, receive, send)
                    return
                chunks.append(chunk)
                if not message.get("more_body", False):
                    break
            body = b"".join(chunks)
            sent = False

            async def replay_body():
                nonlocal sent
                if sent:
                    return {"type": "http.request", "body": b"", "more_body": False}
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}

            await self.app(scope, replay_body, send)
            return
        await self.app(scope, receive, send)


app.add_middleware(HostedDemoBoundaryMiddleware)

class AIRateLimitMiddleware:
    """Bound local-mode metadata inference requests as well."""
    def __init__(self, app): self.app, self.limits = app, {}
    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http" and scope.get("method") == "POST" and scope.get("path") == "/api/ai/metadata":
            client = scope.get("client") or ("unknown", 0); key = str(client[0]); now = time.monotonic()
            start, count = self.limits.get(key, (now, 0))
            if now - start >= 60: start, count = now, 0
            if count >= 8:
                await JSONResponse(status_code=429, content={"detail": "AI request limit reached. Wait a minute and retry."})(scope, receive, send); return
            self.limits[key] = (start, count + 1)
        await self.app(scope, receive, send)

app.add_middleware(AIRateLimitMiddleware)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if settings.DEVSWEEP_HOSTED_DEMO:
        return {"status": "healthy"}
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
    if settings.DEVSWEEP_HOSTED_DEMO:
        return {"hosted_demo": True, "demo_mode": True}
    return {
        "hosted_demo": settings.DEVSWEEP_HOSTED_DEMO,
        "demo_mode": settings.DEVSWEEP_DEMO_MODE,
        "default_risk_level": settings.DEVSWEEP_DEFAULT_RISK_LEVEL,
        **({} if settings.DEVSWEEP_HOSTED_DEMO else {"workspace_root": str(settings.workspace_root)}),
    }


# Import and include routers
from scanner.routes import router as scanner_router
from cleanup.routes import router as cleanup_router
from ai.routes import router as ai_router
from security.routes import router as access_router
from demo_routes import router as hosted_demo_router

app.include_router(scanner_router, prefix="/api/scan", tags=["scanner"])
app.include_router(cleanup_router, prefix="/api/cleanup", tags=["cleanup"])
app.include_router(ai_router, prefix="/api/ai", tags=["ai"])
app.include_router(access_router, prefix="/api/access", tags=["access"])
app.include_router(hosted_demo_router)

# Serve the built frontend from the same origin when a production bundle exists.
_frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_frontend_dist / "assets"), name="frontend-assets")

    @app.get("/", include_in_schema=False)
    async def frontend_index():
        return FileResponse(_frontend_dist / "index.html")

    @app.get("/favicon.svg", include_in_schema=False)
    async def frontend_favicon():
        return FileResponse(_frontend_dist / "favicon.svg")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )
