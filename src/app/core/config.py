import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://arenasync:arenasync@localhost:5432/arenasyncdb",
    )
    auth_secret: str = os.getenv(
        "AUTH_SECRET",
        "arenasync-development-secret",
    )


settings = Settings()
