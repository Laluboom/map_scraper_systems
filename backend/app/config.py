from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379/0"

    sendgrid_api_key: str
    sendgrid_from_email: str
    sendgrid_from_name: str = "John Doe"

    aws_ses_access_key: str = ""
    aws_ses_secret_key: str = ""
    aws_ses_region: str = "us-east-1"

    hunterio_api_key: str
    zerobounce_api_key: str

    proxy_url: str = ""

    secret_key: str
    email_throttle_per_minute: int = 30
    environment: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
