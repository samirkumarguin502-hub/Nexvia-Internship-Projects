from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = 'AIML-02 Medical Imaging API'
    ENVIRONMENT: str = 'development'
    API_V1_PREFIX: str = '/api/v1'
    CORS_ORIGINS: str = 'http://localhost:5173'

    MAX_UPLOAD_MB: int = Field(default=100, gt=0)
    UPLOAD_DIR: str = './data/uploads'

    ORTHANC_ENABLED: bool = False
    ORTHANC_URL: str = 'http://localhost:8042'
    ORTHANC_USERNAME: str = ''
    ORTHANC_PASSWORD: str = ''

    MODEL_DIR: str = './artifacts/models'

    JWT_SECRET_KEY: str = ''
    ACCESS_TOKEN_MINUTES: int = Field(default=60, gt=0)

    AUTH_DB_PATH: str = './data/auth.sqlite3'

    ADMIN_EMAIL: str = ''
    ADMIN_PASSWORD: str = ''
    ADMIN_FULL_NAME: str = 'System Administrator'

    MLFLOW_TRACKING_URI: str = ''
    PUBMED_API_KEY: str = ''

    # Redis-backed authentication rate limiting
    REDIS_URL: str = 'redis://localhost:6379/0'
    LOGIN_RATE_LIMIT_ATTEMPTS: int = Field(default=5, gt=0)
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = Field(default=900, gt=0)

    model_config = SettingsConfigDict(
        env_file='.env',
        extra='ignore',
    )

    @model_validator(mode='after')
    def validate_security_settings(self):
        if self.ENVIRONMENT.lower() in ('production', 'prod'):
            if len(self.JWT_SECRET_KEY) < 32:
                raise ValueError(
                    'JWT_SECRET_KEY must contain at least 32 characters in production'
                )

        return self

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(',')
            if origin.strip()
        ]


settings = Settings()