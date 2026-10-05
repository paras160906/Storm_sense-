import os
from dataclasses import dataclass
from pathlib import Path


from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
MODELS_DIR = BACKEND_DIR / "models"

load_dotenv(BACKEND_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql://stormsense:stormsense@localhost:5432/stormsense"
    )
    model_path: str = os.getenv("MODEL_PATH", str(MODELS_DIR / "stormsense.joblib"))
    nowcast_checkpoint_path: str = os.getenv("NOWCAST_CHECKPOINT_PATH", str(MODELS_DIR / "stormsense.pt"))
    nowcast_config_path: str = os.getenv("NOWCAST_CONFIG_PATH", str(MODELS_DIR / "stormsense.yaml"))
    nowcast_sample_frames_path: str = os.getenv("NOWCAST_SAMPLE_FRAMES_PATH", str(MODELS_DIR / "sample_frames"))
    nowcast_device: str = os.getenv("NOWCAST_DEVICE", "auto")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "groq/compound-mini")


settings = Settings()
