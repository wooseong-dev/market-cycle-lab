from functools import lru_cache
import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    site_name: str = os.getenv("SITE_NAME", "Market Cycle Lab")
    site_url: str = os.getenv("SITE_URL", "http://127.0.0.1:8000").rstrip("/")
    google_site_verification: str = os.getenv("GOOGLE_SITE_VERIFICATION", "")
    naver_site_verification: str = os.getenv("NAVER_SITE_VERIFICATION", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
