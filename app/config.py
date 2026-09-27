import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseModel):
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8080"))
    TEAM_NAME: str = os.getenv("TEAM_NAME", "magicpin-challenge-candidate")
    TEAM_MEMBERS: list[str] = [m.strip() for m in os.getenv("TEAM_MEMBERS", "Candidate").split(",")]
    USE_LLM: bool = os.getenv("USE_LLM", "false").lower() in ("true", "1", "yes")
    MODEL: str = os.getenv("MODEL_NAME", "gpt-4o-mini" if os.getenv("USE_LLM", "false").lower() in ("true", "1", "yes") else "deterministic-rule-engine")
    APPROACH: str = "Deterministic 4-context composition with fact-grounded rules & stateful turn handling"
    CONTACT_EMAIL: str = os.getenv("CONTACT_EMAIL", "candidate@example.com")
    VERSION: str = "1.0.0"
    SUBMITTED_AT: str = "2026-04-26T08:00:00Z"
    
    # LLM configuration (optional with graceful deterministic fallback)
    USE_LLM: bool = os.getenv("USE_LLM", "false").lower() in ("true", "1", "yes")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_TIMEOUT: float = float(os.getenv("LLM_TIMEOUT", "10.0"))
    
    # Dataset path
    DATASET_DIR: Path = BASE_DIR / "dataset"
    EXPANDED_DIR: Path = BASE_DIR / "dataset" / "expanded"

settings = Settings()
