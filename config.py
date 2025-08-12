from pathlib import Path
from typing import List, Dict, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    SECURITY_KEY: str
    PERSON_ID: str
    LOGIN: str
    MAX_FILE_SIZE: int
    NUMBERS_EMOJI: List[str]
    BOT_SESSION_TIMEOUT: int = 60  # в секундах
    DEBUG: bool = False
    # Redis configuration (значения по умолчанию для локальной разработки)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    PYRUS_IDEMPOTENT_TTL: int
    MAX_COUNT_FILES: int
    WEBHOOK_SECURITY_KEY: str
    FORM_TASKS_ID: int
    COOLDOWN_SECONDS: int
    DICT_USER_FIELDS_IDS: Optional[Dict]  = {
        6: "first_phone",
        13: "second_phone",
        7: "email",
        8: "telegram",
        11: "name_pc",
        12: "note",
        9: "whatsapp",

}
    @property
    def MAX_FILE_SIZE_MB(self) -> int:
        return 20

    class Config:
        env_file = str(Path(__file__).parent / ".env")
        env_file_encoding = "utf-8"
settings = Settings() # type: ignore