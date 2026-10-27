import os
from dotenv import load_dotenv

load_dotenv()


def database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./remind-dev.db")
