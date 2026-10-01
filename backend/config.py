from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


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

    # Safety
    DEVSWEEP_DEFAULT_RISK_LEVEL: str = Field(default="SAFE", description="Default risk level for auto-approval")
    DEVSWEEP_MAX_FILE_SIZE: int = Field(default=104857600, description="Max file size to scan (bytes)")

    # Server
    BACKEND_HOST: str = Field(default="0.0.0.0", description="Backend host")
    BACKEND_PORT: int = Field(default=8000, description="Backend port")
    FRONTEND_URL: str = Field(default="http://localhost:5173", description="Frontend URL for CORS")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

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


settings = Settings()
