from flask import Flask

def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",  # busca en la carpeta raíz/templates
        static_folder="../static"       # opcional, para CSS/JS/imagenes
    )

    app.secret_key = "clave_secreta"  # en producción usa config/.env

    # Importar las rutas
    from . import routes
    routes.init_app(app)

    return app
