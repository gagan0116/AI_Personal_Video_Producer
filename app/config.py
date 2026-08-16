import os
from pathlib import Path
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseModel as BaseSettings

class Settings(BaseSettings):
    # LLM Settings (Nemotron Lightning NIM)
    nemotron_url: str = os.getenv("NEMOTRON_URL", "http://localhost:8000/v1")
    nemotron_model: str = os.getenv("NEMOTRON_MODEL", "nemotron-3.5-lightning")
    nemotron_api_key: str = os.getenv("NEMOTRON_API_KEY", "not-needed")

    # NVIDIA VSS Blueprint
    vss_url: str = os.getenv("VSS_URL", "http://localhost:8010")
    vss_enabled: bool = os.getenv("VSS_ENABLED", "false").lower() in ("true", "1", "yes")

    # Storage Paths
    data_dir: str = os.getenv("DATA_DIR", "data/SoccerNet")
    output_dir: str = os.getenv("OUTPUT_DIR", "output")

    # Match Engine simulation settings
    match_speed_multiplier: float = float(os.getenv("MATCH_SPEED_MULTIPLIER", "6.0"))
    window_size_minutes: int = int(os.getenv("WINDOW_SIZE_MINUTES", "5"))

    # Server settings
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8080"))

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
