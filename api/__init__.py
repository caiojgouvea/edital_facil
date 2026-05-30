import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from .config import config

db = SQLAlchemy()


def create_app(env: str | None = None) -> Flask:
    """Cria e configura a aplicação Flask.

    Args:
        env: nome do ambiente ('development', 'production'). Usa FLASK_ENV se omitido.

    Returns:
        Instância configurada do Flask.
    """
    app = Flask(__name__, template_folder="../frontend/templates")

    env = env or os.getenv("FLASK_ENV", "default")
    app.config.from_object(config[env])

    db.init_app(app)

    from .routes.editais import bp as editais_bp
    app.register_blueprint(editais_bp)

    return app
