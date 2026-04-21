from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_token: str
    admin_tg_id: int

    openrouter_api_key: str
    # Free models on OpenRouter (as of 2026-04-20)
    ai_fast_model: str = "google/gemma-4-31b-it:free"   # vision + text, 262k ctx
    ai_smart_model: str = "openai/gpt-oss-120b:free"    # best for reasoning, 131k ctx
    ai_vision_model: str = "google/gemma-4-31b-it:free" # supports image+video

    # Google Gemini (used as primary vision backend — more reliable for photos)
    gemini_api_key: str = ""

    fitbit_client_id: str = ""
    fitbit_client_secret: str = ""

    tts_url: str = ""
    tts_voice: str = "alloy"

    no_gym_warn_days: int = 2
    steps_goal: int = 8000
    daily_check_hour: int = 9
    evening_check_hour: int = 21
    tz: str = "Europe/Moscow"

    db_path: str = "/data/iron_coach.db"

    class Config:
        env_file = ".env"


settings = Settings()
