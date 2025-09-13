from flask import Flask
from app.routes import routes

app = Flask(__name__, template_folder="templates")
app.secret_key = "clave_super_secreta"  # Necesario para sesiones y flash

# Registrar las rutas del Blueprint y mantener el nombre "routes"
app.register_blueprint(routes, url_prefix="/", name="routes")

if __name__ == "__main__":
    app.run(debug=True)
