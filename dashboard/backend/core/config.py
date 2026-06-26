import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    NATS_URL: str = os.environ.get("NATS_URL", "nats://nats:4222")
    NATS_SUBJECT: str = os.environ.get("NATS_SUBJECT", "electricity.silver.demand_5min")
    DATABASE_URL: str = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@postgres:5432/electricity"
    )
    VM_URL: str = os.environ.get("VM_URL", "http://victoriametrics:8428")
    
    class Config:
        env_file = ".env"

settings = Settings()