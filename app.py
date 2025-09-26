from flask import Flask
from app.routes import routes

app = Flask(__name__, template_folder="templates")

# 🔹 Usa una sola clave secreta, bien definida y segura
app.config["SECRET_KEY"] = "clave_super_secreta"  

# Registrar las rutas
app.register_blueprint(routes, url_prefix="/", name="routes")

if __name__ == "__main__":
    app.run(debug=True)
