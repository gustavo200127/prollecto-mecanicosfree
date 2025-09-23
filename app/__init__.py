import os
from flask import Flask

def create_app():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    templates_path = os.path.join(base_dir, "../templates")
    static_path = os.path.join(base_dir, "../static")

    app = Flask(
        __name__,
        template_folder=templates_path,
        static_folder=static_path
    )

    app.secret_key = "clave_secreta"

    from . import routes
    routes.init_app(app)  # Inicializa las rutas/blueprints

    return app
