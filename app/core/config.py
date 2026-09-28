from pydantic_settings import BaseSettings, SettingsConfigDict

# Definición de la clase y metadatos generales

class Settings(BaseSettings):
    PROJECT_NAME: str = "Tarjeta Sanitaria API"
    API_V1_STR: str = "/api/v1"

    # Seguridad y JWT
    SECRET_KEY: str = "clave-secreta-temporal-cambiar-en-produccion"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 horas para login
    QR_TOKEN_EXPIRE_MINUTES: int = 15  # 15 minutos para token efímero QR

    # Base de datos
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/tarjeta_sanitaria"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()