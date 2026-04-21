from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    telegram_token: str
    admin_tg_id: int

    openrouter_api_key: str
    ai_fast_model: str = "google/gemini-flash-1.5"
    ai_smart_model: str = "anthropic/claude-3.5-sonnet"

    fitbit_client_id: str = ""
    fitbit_client_secret: str = ""

    tts_url: str = ""
    tts_voice: str = "alloy"

    no_gym_warn_days: int = 2
    steps_goal: int = 8000
    daily_check_hour: int = 9
    evening_check_hour: int = 21

    db_path: str = "/data/iron_coach.db"

    class Config:
        env_file = ".env"


settings = Settings()
