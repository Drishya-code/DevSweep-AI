from pathlib import Path
from typing import Optional
import ipaddress
from urllib.parse import urlsplit
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    # Nebius Token Factory + NVIDIA Nemotron
    NEBIUS_API_KEY: Optional[str] = Field(default=None, description="Nebius Token Factory API key")
    NEBIUS_BASE_URL: str = Field(default="https://api.tokenfactory.us-central1.nebius.com/v1/", description="Nebius API base URL")
    NEBIUS_MODEL: str = Field(default="nvidia/nemotron-3-super-120b-a12b", description="Model name to use")

    # Workspace
    DEVSWEEP_WORKSPACE_ROOT: Optional[str] = Field(default=None, description="Root directory to scan")
    DEVSWEEP_DEMO_MODE: bool = Field(default=False, description="Enable demo fixture mode")

    # Storage
    DEVSWEEP_DB_PATH: str = Field(default="./data/devsweep.db", description="SQLite database path")
    DEVSWEEP_BACKUP_ROOT: Optional[str] = Field(default=None, description="Private content-backup directory; defaults to the per-user application data directory")

    # Safety
    DEVSWEEP_DEFAULT_RISK_LEVEL: str = Field(default="SAFE", description="Default risk level for auto-approval")
    DEVSWEEP_MAX_FILE_SIZE: int = Field(default=104857600, description="Max file size to scan (bytes)")

    # Server
    BACKEND_HOST: str = Field(default="127.0.0.1", description="Loopback-only backend host")
    BACKEND_PORT: int = Field(default=8000, description="Backend port")
    FRONTEND_URL: str = Field(default="http://localhost:5173", description="Frontend URL for CORS")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    @field_validator("BACKEND_HOST")
    @classmethod
    def require_loopback_backend_host(cls, value: str) -> str:
        try:
            loopback = value.lower() == "localhost" or ipaddress.ip_address(value).is_loopback
        except ValueError:
            loopback = False
        if not loopback:
            raise ValueError(
                "BACKEND_HOST must be localhost or a loopback IP. Remote binding is disabled until authentication is implemented."
            )
        return value

    @field_validator("FRONTEND_URL")
    @classmethod
    def require_loopback_frontend_origin(cls, value: str) -> str:
        parsed = urlsplit(value)
        try:
            loopback = parsed.hostname and (
                parsed.hostname.lower() == "localhost"
                or ipaddress.ip_address(parsed.hostname).is_loopback
            )
        except ValueError:
            loopback = False
        if (
            parsed.scheme not in {"http", "https"}
            or not loopback
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("FRONTEND_URL must be a local loopback origin.")
        return value.rstrip("/")

    class Config:
        # Support the repository-root example and existing backend/.env files
        # independently of the process working directory. Backend settings win.
        env_file = (
            Path(__file__).resolve().parent.parent / ".env",
            Path(__file__).resolve().parent / ".env",
        )
        env_file_encoding = "utf-8"
        case_sensitive = True

    @property
    def workspace_root(self) -> Path:
        if self.DEVSWEEP_WORKSPACE_ROOT:
            return Path(self.DEVSWEEP_WORKSPACE_ROOT).resolve()
        return Path.cwd()

    @property
    def db_path(self) -> Path:
        path = Path(self.DEVSWEEP_DB_PATH)
        if not path.is_absolute():
            path = self.workspace_root / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def backup_root(self) -> Path:
        if self.DEVSWEEP_BACKUP_ROOT:
            return Path(self.DEVSWEEP_BACKUP_ROOT).expanduser().resolve(strict=False)
        import os
        if os.environ.get("LOCALAPPDATA"):
            root = Path(os.environ["LOCALAPPDATA"]) / "DevSweepAI" / "backups"
        elif os.environ.get("XDG_DATA_HOME"):
            root = Path(os.environ["XDG_DATA_HOME"]) / "devsweep-ai" / "backups"
        else:
            root = Path.home() / ".local" / "share" / "devsweep-ai" / "backups"
        return root.resolve(strict=False)


settings = Settings()
