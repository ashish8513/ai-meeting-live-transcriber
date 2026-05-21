import os
from functools import lru_cache


@lru_cache
def get_settings():
    return Settings()


class Settings:
    def __init__(self):
        self.database_url = os.getenv(
            "DATABASE_URL",
            "sqlite:///./data/meetscribe.db",
        )
        self.jwt_secret = os.getenv("JWT_SECRET", "change-me-in-production-use-long-random-string")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
        self.internal_api_key = os.getenv("INTERNAL_API_KEY", "dev-internal-key-change-me")
        self.cors_origins = [
            o.strip()
            for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
            if o.strip()
        ]
        seed = os.getenv("ADMIN_EMAIL", "").strip().lower()
        self.admin_email = seed if seed else None
