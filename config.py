import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # 🔐 Seguridad general
    SECRET_KEY = os.getenv("SECRET_KEY", "default_secret")

    # 🔗 Base de datos
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ⚡ Seguridad login
    MAX_INTENTOS = int(os.getenv("MAX_INTENTOS", 3))          # intentos fallidos permitidos
    TIEMPO_BLOQUEO_MIN = int(os.getenv("TIEMPO_BLOQUEO_MIN", 5))  # minutos de bloqueo
