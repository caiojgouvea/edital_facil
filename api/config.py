import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configurações base compartilhadas por todos os ambientes."""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "..", "uploads")
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB

    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")
    S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
    S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
    S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
    S3_BUCKET = os.getenv("S3_BUCKET", "editais")


class DevelopmentConfig(Config):
    """Configurações de desenvolvimento com SQLite local."""
    DEBUG = True
    _base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(_base, 'instance', 'db.sqlite')}",
    )


class ProductionConfig(Config):
    """Configurações de produção — DATABASE_URL obrigatória via variável de ambiente."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
