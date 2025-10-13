import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class AppConfig:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///local.db")
    secret_token: str = os.getenv("SECRET_TOKEN", "dev-token")
    cors_origin: str = os.getenv("CORS_ORIGIN", "http://localhost:5173")

    def apply(self, app) -> None:
        app.config["SQLALCHEMY_DATABASE_URI"] = self.database_url
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        app.config["SECRET_TOKEN"] = self.secret_token
