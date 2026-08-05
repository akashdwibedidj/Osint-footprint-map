from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_url: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str

    # Tool binary/command overrides. Defaults assume the tool is on PATH
    # (e.g. installed via `pip install sherlock-project` / `pip install maigret`
    # inside the backend's venv). Override in .env if a tool needs a full path
    # or extra flags, e.g. MAIGRET_CMD=/opt/venv/Scripts/maigret.exe
    sherlock_cmd: str = "sherlock"
    maigret_cmd: str = "maigret"

    class Config:
        env_file = ".env"


settings = Settings()
