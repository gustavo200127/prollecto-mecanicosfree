from flask import Blueprint, render_template, request, redirect, url_for, flash, session
import mysql.connector
from functools import wraps
import re          # <-- necesario para expresiones regulares
import bcrypt      # <-- necesario para hashear contraseñas

routes = Blueprint("routes", __name__)

# --------------------------
# Conexión a la BD
# --------------------------
def conectar_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="mecanicosfree"
    )

# --------------------------
# DECORADOR PARA RUTAS PROTEGIDAS POR ROL
# --------------------------
def login_required(rol=None):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "usuario" not in session:
                flash("Debes iniciar sesión ❌", "danger")
                return redirect(url_for("routes.login"))
            if rol and session["usuario"]["rol"] != rol:
                flash("Acceso no autorizado ❌", "danger")
                return redirect(url_for("routes.login"))
            return f(*args, **kwargs)
        return decorated
    return wrapper

# --------------------------
# INICIO
# --------------------------
@routes.route("/")
def inicio():
    return render_template("index.html")

# --------------------------
# CATÁLOGO
# --------------------------
@routes.route("/catalogo")
def catalogo():
    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT p.*, u.nombre_usu AS taller
        FROM producto p
        JOIN usuario u ON p.id_usutaller = u.numdocumento
    """)
    productos = cursor.fetchall()

    cursor.execute("""
        SELECT s.*, u.nombre_usu AS taller
        FROM servicio s
        JOIN usuario u ON s.id_usutaller = u.numdocumento
    """)
    servicios = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("catalogo.html", productos=productos, servicios=servicios)

# --------------------------
# LOGIN UNIFICADO (cliente / taller / admin)
# --------------------------
@routes.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form.get("correoElectronico")
        contrasena_ingresada = request.form.get("contrasena")

        conn = conectar_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.numdocumento, u.nombre_usu, u.correoElectronico, u.activo, r.tipoRol, u.contrasena
            FROM usuario u
            JOIN rol r ON u.numdocumento = r.numdocumento
            WHERE u.correoElectronico=%s
        """, (correo,))
        usuario = cursor.fetchone()
        conn.close()

        if usuario:
            if not usuario["activo"]:
                flash("Tu cuenta ha sido deshabilitada ❌", "danger")
                return redirect(url_for("routes.login"))

            # 1️⃣ Verificar contraseña con bcrypt
            hash_guardado = usuario["contrasena"]
            if not bcrypt.checkpw(contrasena_ingresada.encode('utf-8'), hash_guardado.encode('utf-8')):
                flash("Correo o contraseña incorrectos ❌", "danger")
                return redirect(url_for("routes.login"))

            # 2️⃣ Guardar sesión
            session["usuario"] = {
                "numdocumento": usuario["numdocumento"],
                "nombre_usu": usuario["nombre_usu"],
                "correoElectronico": usuario["correoElectronico"],
                "rol": usuario["tipoRol"]
            }
            flash("Inicio de sesión exitoso ✅", "success")

            # 3️⃣ Redirección según rol
            rol = usuario["tipoRol"]
            if rol == "admin":
                return redirect(url_for("routes.admin_dashboard"))
            elif rol == "taller":
                return redirect(url_for("routes.perfil_taller"))
            else:
                return redirect(url_for("routes.perfil_cliente"))
        else:
            flash("Correo o contraseña incorrectos ❌", "danger")

    return render_template("login.html")

# --------------------------
# PERFIL CLIENTE
# --------------------------
@routes.route("/perfil_cliente")
@login_required(rol="cliente")
def perfil_cliente():
    return render_template("perfil_cliente.html", usuario=session["usuario"])
    
# --------------------------
# LOGOUT UNIFICADO
# --------------------------
@routes.route("/logout")
def logout():
    session.pop("usuario", None)
    flash("Sesión cerrada ✅", "info")
    return redirect(url_for("routes.login"))    

# --------------------------
# PERFIL TALLER
# --------------------------
@routes.route("/perfil_taller")
@login_required(rol="taller")
def perfil_taller():
    return render_template("perfil_taller.html", usuario=session["usuario"])

# --------------------------
# DASHBOARD ADMIN
# --------------------------
@routes.route("/admin/dashboard")
@login_required(rol="admin")
def admin_dashboard():
    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM usuario")
    total_usuarios = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM rol WHERE tipoRol = 'taller'")
    total_talleres = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM producto")
    total_productos = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM servicio")
    total_servicios = cursor.fetchone()["total"]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_usuarios=total_usuarios,
        total_talleres=total_talleres,
        total_productos=total_productos,
        total_servicios=total_servicios
    )

# --------------------------
# REGISTRAR USUARIO
# --------------------------
@routes.route("/usuarios/registrar", methods=["GET", "POST"])
def registrar_usuario():
    if request.method == "POST":
        numdocumento = request.form["numdocumento"]
        nombre_usu = request.form["nombre_usu"]
        correoElectronico = request.form["correoElectronico"]
        contrasena = request.form["contrasena"]
        contrasena2 = request.form.get("contrasena2")
        rol = request.form.get("rol", "cliente")

        # 1️⃣ Validar que las contraseñas coincidan
        if contrasena != contrasena2:
            flash("Las contraseñas no coinciden ❌", "danger")
            return redirect(url_for("routes.registrar_usuario"))

        # 2️⃣ Validar contraseña mínima 8 caracteres con letras y números
        if not re.match(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$', contrasena):
            flash("La contraseña debe tener al menos 8 caracteres, incluyendo letras y números ❌", "danger")
            return redirect(url_for("routes.registrar_usuario"))

        # 3️⃣ Hashear la contraseña con bcrypt
        hashed = bcrypt.hashpw(contrasena.encode('utf-8'), bcrypt.gensalt())

        # 4️⃣ Conectar a la base de datos
        conn = conectar_db()
        cursor = conn.cursor(dictionary=True)

        # 5️⃣ Verificar si el documento o correo ya existen
        cursor.execute(
            "SELECT * FROM usuario WHERE numdocumento=%s OR correoElectronico=%s",
            (numdocumento, correoElectronico)
        )
        existente = cursor.fetchone()

        if existente:
            flash("El documento o correo ya está registrado ❌", "danger")
            conn.close()
            return redirect(url_for("routes.registrar_usuario"))

        # 6️⃣ Insertar usuario en la tabla 'usuario'
        cursor.execute(
            "INSERT INTO usuario (numdocumento, nombre_usu, correoElectronico, contrasena) VALUES (%s, %s, %s, %s)",
            (numdocumento, nombre_usu, correoElectronico, hashed.decode('utf-8'))
        )
        conn.commit()

        # 7️⃣ Ajustar rol según la selección
        rol_db = "pendiente_taller" if rol == "taller" else "cliente"

        # 8️⃣ Insertar rol en la tabla 'rol'
        cursor.execute(
            "INSERT INTO rol (numdocumento, tipoRol) VALUES (%s, %s)",
            (numdocumento, rol_db)
        )
        conn.commit()
        conn.close()

        flash("Usuario registrado con éxito ✅", "success")
        return redirect(url_for("routes.login"))

    # Si es GET, mostrar el formulario
    return render_template("registrar_usuario.html")

# --------------------------
# LISTAR USUARIOS (solo admin)
# --------------------------
@routes.route("/usuarios")
@login_required(rol="admin")
def usuarios():
    # Obtener la página actual desde query string (?page=1)
    page = request.args.get("page", 1, type=int)
    per_page = 10  # número de usuarios por página
    offset = (page - 1) * per_page

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    
    # Total de usuarios para calcular páginas
    cursor.execute("SELECT COUNT(*) AS total FROM usuario")
    total_usuarios = cursor.fetchone()["total"]

    # Obtener solo los usuarios de la página actual
    cursor.execute(
        "SELECT * FROM usuario ORDER BY nombre_usu ASC LIMIT %s OFFSET %s",
        (per_page, offset)
    )
    lista_usuarios = cursor.fetchall()
    
    conn.close()

    total_pages = (total_usuarios + per_page - 1) // per_page  # ceil division

    return render_template(
        "admin_usuarios.html",
        usuarios=lista_usuarios,
        page=page,
        total_pages=total_pages
    )



# --------------------------
# EDITAR USUARIO (ADMIN)
# --------------------------
@routes.route("/usuarios/editar/<numdocumento>", methods=["GET", "POST"])
def editar_usuario(numdocumento):
    if "usuario" not in session or session["usuario"]["rol"] != "admin":
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login"))

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuario WHERE numdocumento = %s", (numdocumento,))
    usuario = cursor.fetchone()

    if not usuario:
        flash("Usuario no encontrado ❌", "danger")
        conn.close()
        return redirect(url_for("routes.usuarios"))

    if request.method == "POST":
        nombre_usu = request.form["nombre_usu"]
        correoElectronico = request.form["correoElectronico"]
        contrasena = request.form.get("contrasena")
        contrasena2 = request.form.get("contrasena2")

        if contrasena or contrasena2:
            if contrasena != contrasena2:
                flash("Las contraseñas no coinciden ❌", "danger")
                return redirect(url_for("routes.editar_usuario", numdocumento=numdocumento))
            cursor.execute(
                "UPDATE usuario SET nombre_usu=%s, correoElectronico=%s, contrasena=%s WHERE numdocumento=%s",
                (nombre_usu, correoElectronico, contrasena, numdocumento)
            )
        else:
            cursor.execute(
                "UPDATE usuario SET nombre_usu=%s, correoElectronico=%s WHERE numdocumento=%s",
                (nombre_usu, correoElectronico, numdocumento)
            )

        conn.commit()
        conn.close()
        flash("Usuario actualizado ✅", "success")
        return redirect(url_for("routes.usuarios"))

    conn.close()
    return render_template("editar_usuario.html", usuario=usuario)

# --------------------------
# DESHABILITAR / HABILITAR USUARIO (ADMIN)
# --------------------------
@routes.route("/usuarios/toggle/<numdocumento>", methods=["POST"])
def toggle_usuario(numdocumento):
    if "usuario" not in session or session["usuario"]["rol"] != "admin":
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login"))

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)

    # Consultar estado actual del usuario (forzar a 0 si es NULL)
    cursor.execute("SELECT IFNULL(activo, 0) AS activo FROM usuario WHERE numdocumento = %s", (numdocumento,))
    usuario = cursor.fetchone()

    if not usuario:
        conn.close()
        flash("Usuario no encontrado ❌", "danger")
        return redirect(url_for("routes.usuarios"))

    # Convertir a entero sí o sí
    estado_actual = int(usuario["activo"])

    # Alternar estado
    nuevo_estado = 0 if estado_actual == 1 else 1

    cursor.execute("UPDATE usuario SET activo = %s WHERE numdocumento = %s", (nuevo_estado, numdocumento))
    conn.commit()
    conn.close()

    if nuevo_estado == 1:
        flash("Usuario habilitado ✅", "success")
    else:
        flash("Usuario deshabilitado ❌", "warning")

    return redirect(url_for("routes.usuarios"))


# --------------------------
# ADMIN - PRODUCTOS
# --------------------------
@routes.route("/admin/productos")
def admin_productos():
    if "usuario" not in session or session["usuario"]["rol"] != "admin":
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login"))

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.*, u.nombre_usu AS taller
        FROM producto p
        JOIN usuario u ON p.id_usutaller = u.numdocumento
    """)
    productos = cursor.fetchall()
    conn.close()

    return render_template("admin_productos.html", productos=productos)

# --------------------------
# ADMIN - SERVICIOS
# --------------------------
@routes.route("/admin/servicios")
def admin_servicios():
    if "usuario" not in session or session["usuario"]["rol"] != "admin":
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login"))

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.*, u.nombre_usu AS taller
        FROM servicio s
        JOIN usuario u ON s.id_usutaller = u.numdocumento
    """)
    servicios = cursor.fetchall()
    conn.close()

    return render_template("admin_servicios.html", servicios=servicios)

# --------------------------
# AGREGAR SERVICIO (TALLER)
# --------------------------
@routes.route("/agregar_servicio", methods=["GET", "POST"])
def agregar_servicio():
    if "usuario" not in session or session["usuario"].get("rol") != "taller":
        flash("Acceso no autorizado ❌", "danger")
        return redirect(url_for("routes.login"))

    if request.method == "POST":
        tipo_servicio = request.form["tipo_servicio"]
        precio = request.form["precio"]
        disponibilidad = request.form["disponibilidad"]

        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO servicio (tipo_servicio, precio, disponibilidad, id_usutaller)
            VALUES (%s, %s, %s, %s)
        """, (tipo_servicio, precio, disponibilidad, session["usuario"]["numdocumento"]))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Servicio agregado correctamente ✅", "success")
        return redirect(url_for("routes.perfil_taller"))

    return render_template("agregar_servicio.html")

# --------------------------
# AGREGAR PRODUCTO (TALLER)
# --------------------------
@routes.route("/productos/agregar", methods=["GET", "POST"])
def agregar_producto():
    if "usuario" not in session or session["usuario"]["rol"] != "taller":
        flash("Acceso no autorizado ❌", "danger")
        return redirect(url_for("routes.login"))

    if request.method == "POST":
        tipo_producto = request.form.get("tipo_producto")
        marca_producto = request.form.get("marca_producto")
        precio_producto = request.form.get("precio_producto")
        stock_producto = request.form.get("stock_producto")

        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO producto (id_usutaller, tipo_producto, marca_producto, precio_producto, stock_producto, publicado)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            session["usuario"]["numdocumento"],
            tipo_producto,
            marca_producto,
            precio_producto,
            stock_producto,
            "publicado"
        ))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Producto agregado con éxito ✅", "success")
        return redirect(url_for("routes.perfil_taller"))

    return render_template("agregar_producto.html")

# --------------------------
# AGREGAR VEHÍCULO (CLIENTE)
# --------------------------
@routes.route("/agregar_vehiculo", methods=["GET", "POST"])
def agregar_vehiculo():
    if "usuario" not in session or session["usuario"].get("rol") != "cliente":
        flash("Acceso no autorizado ❌", "danger")
        return redirect(url_for("routes.login"))

    if request.method == "POST":
        tipo_vehiculo = request.form["tipo_vehiculo"]
        modelo_vehiculo = request.form["modelo_vehiculo"]

        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO vehiculos (tipo_vehiculo, modelo_vehiculo, id_usucliente)
            VALUES (%s, %s, %s)
        """, (tipo_vehiculo, modelo_vehiculo, session["usuario"]["numdocumento"]))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Vehículo registrado correctamente ✅", "success")
        return redirect(url_for("routes.perfil_cliente"))

    return render_template("agregar_vehiculo.html")

# --------------------------
# ADMIN - PUBLICACIONES
# --------------------------
@routes.route("/admin/publicaciones")
def admin_publicaciones():
    # Validar que el usuario sea admin
    if "usuario" not in session or session["usuario"]["rol"] != "admin":
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login"))

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT rp.*, u.nombre_usu AS taller
        FROM registro_publicaciones rp
        JOIN usuario u ON rp.id_usutaller = u.numdocumento
    """)
    publicaciones = cursor.fetchall()
    conn.close()

    return render_template("admin_publicaciones.html", publicaciones=publicaciones)


# --------------------------
# ADMIN - VER DETALLE PRODUCTO
# --------------------------
@routes.route("/admin/producto/<int:id_producto>")
def admin_ver_producto(id_producto):
    if "usuario" not in session or session["usuario"]["rol"] != "admin":
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login"))

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.*, u.nombre_usu AS taller, u.correoElectronico
        FROM producto p
        JOIN usuario u ON p.id_usutaller = u.numdocumento
        WHERE p.id_producto = %s
    """, (id_producto,))
    producto = cursor.fetchone()
    conn.close()

    if not producto:
        flash("Producto no encontrado ❌", "danger")
        return redirect(url_for("routes.admin_publicaciones"))

    return render_template("admin_ver_producto.html", producto=producto)


# --------------------------
# ADMIN - VER DETALLE SERVICIO
# --------------------------
@routes.route("/admin/servicio/<int:id_servicio>")
def admin_ver_servicio(id_servicio):
    if "usuario" not in session or session["usuario"]["rol"] != "admin":
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login"))

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.*, u.nombre_usu AS taller, u.correoElectronico
        FROM servicio s
        JOIN usuario u ON s.id_usutaller = u.numdocumento
        WHERE s.id_servicio = %s
    """, (id_servicio,))
    servicio = cursor.fetchone()
    conn.close()

    if not servicio:
        flash("Servicio no encontrado ❌", "danger")
        return redirect(url_for("routes.admin_publicaciones"))

    return render_template("admin_ver_servicio.html", servicio=servicio)


# --------------------------
# ADMIN - SOLICITUDES DE TALLER
# --------------------------
@routes.route("/admin/solicitudes_taller")
def solicitudes_taller():
    if "usuario" not in session or session["usuario"]["rol"] != "admin":
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login"))

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.numdocumento, u.nombre_usu, u.correoElectronico, r.tipoRol
        FROM usuario u
        JOIN rol r ON u.numdocumento = r.numdocumento
        WHERE r.tipoRol = 'pendiente_taller'
    """)
    solicitudes = cursor.fetchall()
    conn.close()

    return render_template("admin_solicitudes_taller.html", solicitudes=solicitudes)


# --------------------------
# ADMIN - ACEPTAR TALLER
# --------------------------
@routes.route("/admin/solicitudes_taller/aceptar/<int:numdocumento>")
def aceptar_taller(numdocumento):
    if "usuario" not in session or session["usuario"]["rol"] != "admin":
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login"))

    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE rol SET tipoRol = 'taller' WHERE numdocumento = %s", (numdocumento,))
    conn.commit()
    conn.close()

    flash("Taller aprobado con éxito ✅", "success")
    return redirect(url_for("routes.solicitudes_taller"))


# --------------------------
# ADMIN - RECHAZAR TALLER
# --------------------------
@routes.route("/admin/solicitudes_taller/rechazar/<int:numdocumento>")
def rechazar_taller(numdocumento):
    if "usuario" not in session or session["usuario"]["rol"] != "admin":
        flash("Debes iniciar sesión como administrador", "warning")
        return redirect(url_for("routes.login"))

    conn = conectar_db()
    cursor = conn.cursor()
    # eliminamos el rol y el usuario
    cursor.execute("DELETE FROM rol WHERE numdocumento = %s", (numdocumento,))
    cursor.execute("DELETE FROM usuario WHERE numdocumento = %s", (numdocumento,))
    conn.commit()
    conn.close()

    flash("Solicitud de taller rechazada ❌", "info")
    return redirect(url_for("routes.solicitudes_taller"))

# --------------------------
# AGREGAR PRODUCTO AL CARRITO (permitir cliente o taller)
# --------------------------
@routes.route("/carrito/agregar/<int:id_producto>", methods=["POST"])
def carrito_agregar(id_producto):
    if "usuario" not in session or session["usuario"]["rol"] not in ["cliente", "taller"]:
        flash("Debes iniciar sesión como cliente o taller para comprar ❌", "danger")
        return redirect(url_for("routes.login"))

    try:
        cantidad = int(request.form.get("cantidad", 1))
    except (ValueError, TypeError):
        cantidad = 1

    if cantidad <= 0:
        flash("La cantidad debe ser mayor a 0 ❌", "danger")
        return redirect(url_for("routes.catalogo"))

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id_producto, tipo_producto, marca_producto, precio_producto, stock_producto
        FROM producto
        WHERE id_producto=%s
    """, (id_producto,))
    producto = cursor.fetchone()
    conn.close()

    if not producto:
        flash("Producto no encontrado ❌", "danger")
        return redirect(url_for("routes.catalogo"))

    if producto.get("stock_producto", 0) < cantidad:
        flash(f"Solo hay {producto['stock_producto']} unidades disponibles ❌", "danger")
        return redirect(url_for("routes.catalogo"))

    if "carrito" not in session:
        session["carrito"] = []

    # Revisar si ya está en el carrito -> aumentar cantidad
    for item in session["carrito"]:
        if item.get("tipo") == "producto" and item.get("id_producto") == producto["id_producto"]:
            if item["cantidad"] + cantidad > producto["stock_producto"]:
                flash(f"No puedes agregar más de {producto['stock_producto']} unidades ❌", "danger")
                return redirect(url_for("routes.catalogo"))
            item["cantidad"] += cantidad
            break
    else:
        session["carrito"].append({
            "tipo": "producto",
            "id_producto": producto["id_producto"],
            "nombre": f"{producto['tipo_producto']} - {producto['marca_producto']}",
            "precio": float(producto["precio_producto"]),
            "cantidad": cantidad
        })

    session.modified = True
    flash(f"{cantidad} unidad(es) agregada(s) al carrito 🛒", "success")
    return redirect(url_for("routes.catalogo"))


# --------------------------
# AGREGAR SERVICIO AL CARRITO (1 en 1)
# --------------------------
@routes.route("/carrito/agregar_servicio/<int:id_servicio>", methods=["POST"])
def carrito_agregar_servicio(id_servicio):
    if "usuario" not in session or session["usuario"]["rol"] not in ["cliente", "taller"]:
        flash("Debes iniciar sesión como cliente o taller para pedir un servicio ❌", "danger")
        return redirect(url_for("routes.login"))

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id_servicio, tipo_servicio, precio, disponibilidad FROM servicio WHERE id_servicio=%s", (id_servicio,))
    servicio = cursor.fetchone()
    conn.close()

    if not servicio or servicio["disponibilidad"] != 1:
        flash("Servicio no disponible ❌", "danger")
        return redirect(url_for("routes.catalogo"))

    if "carrito" not in session:
        session["carrito"] = []

    # Evitar duplicados: 1 por 1
    for item in session["carrito"]:
        if item.get("tipo") == "servicio" and item.get("id_servicio") == id_servicio:
            flash("Este servicio ya está en el carrito ❌", "info")
            return redirect(url_for("routes.catalogo"))

    session["carrito"].append({
        "tipo": "servicio",
        "id_servicio": servicio["id_servicio"],
        "nombre": servicio["tipo_servicio"],
        "precio": float(servicio["precio"]),
        "cantidad": 1
    })

    session.modified = True
    flash("Servicio agregado al carrito 🛒", "success")
    return redirect(url_for("routes.catalogo"))



# --------------------------
# VER CARRITO
# --------------------------
@routes.route("/carrito")
def carrito_ver():
    carrito = session.get("carrito", [])
    total = sum(item["precio"] * item["cantidad"] for item in carrito) if carrito else 0
    return render_template("carrito.html", carrito=carrito, total=total)


# --------------------------
# ELIMINAR ITEM DEL CARRITO
# --------------------------
@routes.route("/carrito/eliminar/<tipo>/<int:id_item>")
def carrito_eliminar(tipo, id_item):
    if "carrito" in session:
        if tipo == "producto":
            session["carrito"] = [item for item in session["carrito"] if not (item.get("tipo")=="producto" and item.get("id_producto")==id_item)]
        elif tipo == "servicio":
            session["carrito"] = [item for item in session["carrito"] if not (item.get("tipo")=="servicio" and item.get("id_servicio")==id_item)]
        session.modified = True
        flash("Item eliminado del carrito ❌", "info")
    return redirect(url_for("routes.carrito_ver"))


# --------------------------
# FINALIZAR COMPRA OPTIMIZADO
# --------------------------
@routes.route("/carrito/finalizar", methods=["GET","POST"])
def carrito_finalizar():
    if "usuario" not in session or session["usuario"]["rol"] not in ["cliente","taller"]:
        flash("Debes iniciar sesión para comprar ❌", "danger")
        return redirect(url_for("routes.login"))

    id_usuario = session["usuario"]["numdocumento"]

    # Verificar vehículo para clientes
    if session["usuario"]["rol"] == "cliente":
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vehiculos WHERE id_usucliente=%s", (id_usuario,))
        tiene_vehiculo = cursor.fetchone()[0]
        conn.close()
        if tiene_vehiculo == 0:
            flash("Debes registrar un vehículo antes de realizar compras 🚗❌","danger")
            return redirect(url_for("routes.agregar_vehiculo"))

    carrito = session.get("carrito", [])
    if not carrito:
        flash("Tu carrito está vacío 🛒","info")
        return redirect(url_for("routes.catalogo"))

    conn = conectar_db()
    cursor = conn.cursor()

    try:
        # Crear factura
        cursor.execute("INSERT INTO factura (id_cliente, total) VALUES (%s, 0)", (id_usuario,))
        conn.commit()
        factura_id = cursor.lastrowid

        total_factura = 0

        for item in carrito:
            if item["tipo"] == "producto":
                subtotal = item["precio"] * item["cantidad"]
                total_factura += subtotal

                cursor.execute("""
                    INSERT INTO detalle_factura (id_factura, id_producto, cantidad, precio_unitario, subtotal)
                    VALUES (%s, %s, %s, %s, %s)
                """, (factura_id, item["id_producto"], item["cantidad"], item["precio"], subtotal))

                cursor.execute("""
                    UPDATE producto SET stock_producto = stock_producto - %s
                    WHERE id_producto = %s
                """, (item["cantidad"], item["id_producto"]))

            elif item["tipo"] == "servicio":
                subtotal = item["precio"]
                total_factura += subtotal

                cursor.execute("""
                    INSERT INTO detalle_factura (id_factura, id_servicio, cantidad, precio_unitario, subtotal)
                    VALUES (%s, %s, 1, %s, %s)
                """, (factura_id, item["id_servicio"], item["precio"], subtotal))

        cursor.execute("UPDATE factura SET total=%s WHERE id_factura=%s", (total_factura, factura_id))
        conn.commit()

        flash(f"Compra registrada ✅ Factura #{factura_id} generada", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Ocurrió un error al finalizar la compra: {str(e)}", "danger")
    finally:
        cursor.close()
        conn.close()

    session.pop("carrito", None)
    session.modified = True
    return redirect(url_for("routes.perfil_cliente"))

# --------------------------
# RUTAS PARA FACTURAS (USUARIO)
# --------------------------
@routes.route("/mis_facturas")
def mis_facturas():
    if "usuario" not in session:
        flash("Debes iniciar sesión para ver tus facturas", "warning")
        return redirect(url_for("routes.login"))

    id_usuario = session["usuario"]["numdocumento"]
    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT f.id_factura, f.fecha_emision, f.total
        FROM factura f
        WHERE f.id_cliente = %s
        ORDER BY f.fecha_emision DESC
    """, (id_usuario,))
    facturas = cursor.fetchall()
    conn.close()
    return render_template("mis_facturas.html", facturas=facturas)


@routes.route("/factura/<int:id_factura>")
def ver_factura(id_factura):
    if "usuario" not in session:
        flash("Debes iniciar sesión para ver la factura", "warning")
        return redirect(url_for("routes.login"))

    id_usuario = session["usuario"]["numdocumento"]
    is_admin = "admin" in session

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)

    # Verificar existencia y permisos
    cursor.execute("SELECT id_cliente, fecha_emision FROM factura WHERE id_factura = %s", (id_factura,))
    factura = cursor.fetchone()
    if not factura:
        conn.close()
        flash("Factura no encontrada ❌", "danger")
        return redirect(url_for("routes.mis_facturas"))

    if factura["id_cliente"] != id_usuario and not is_admin:
        conn.close()
        flash("No tienes permiso para ver esta factura ❌", "danger")
        return redirect(url_for("routes.mis_facturas"))

    # Obtener detalles de productos y servicios con estado del taller
    cursor.execute("""
        SELECT d.id_detalle,
               CASE 
                   WHEN d.id_producto IS NOT NULL THEN p.tipo_producto
                   WHEN d.id_servicio IS NOT NULL THEN s.tipo_servicio
                   ELSE 'Desconocido'
               END AS nombre,
               CASE 
                   WHEN d.id_producto IS NOT NULL THEN 'Producto'
                   WHEN d.id_servicio IS NOT NULL THEN 'Servicio'
                   ELSE 'Desconocido'
               END AS tipo,
               p.marca_producto,
               d.cantidad,
               d.precio_unitario,
               d.subtotal,
               COALESCE(d.estado_taller, 'pendiente') AS estado_taller
        FROM detalle_factura d
        LEFT JOIN producto p ON d.id_producto = p.id_producto
        LEFT JOIN servicio s ON d.id_servicio = s.id_servicio
        WHERE d.id_factura = %s
    """, (id_factura,))
    detalles = cursor.fetchall()

    # Calcular total dinámicamente
    total = sum(item["subtotal"] for item in detalles)
    factura["total"] = total

    conn.close()
    return render_template("ver_factura.html", factura=factura, detalles=detalles)


# --------------------------
# AGREGAR SERVICIO A FACTURA
# --------------------------
@routes.route("/factura/agregar_servicio/<int:id_servicio>", methods=["POST"])
def agregar_servicio_factura(id_servicio):
    if "usuario" not in session:
        flash("Debes iniciar sesión para contratar un servicio", "warning")
        return redirect(url_for("routes.login"))

    id_usuario = session["usuario"]["numdocumento"]
    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)

    # Obtener la última factura del usuario o crear una nueva
    cursor.execute("""
        SELECT id_factura FROM factura
        WHERE id_cliente = %s
        ORDER BY fecha_emision DESC
        LIMIT 1
    """, (id_usuario,))
    factura = cursor.fetchone()

    if not factura:
        cursor.execute("INSERT INTO factura (id_cliente, total) VALUES (%s, 0)", (id_usuario,))
        conn.commit()
        factura_id = cursor.lastrowid
    else:
        factura_id = factura["id_factura"]

    # Obtener precio del servicio
    cursor.execute("SELECT precio FROM servicio WHERE id_servicio = %s", (id_servicio,))
    serv = cursor.fetchone()
    if not serv:
        conn.close()
        flash("El servicio no existe ❌", "danger")
        return redirect(url_for("routes.mis_facturas"))

    precio = serv["precio"]

    # Insertar servicio en detalle_factura con estado pendiente
    cursor.execute("""
        INSERT INTO detalle_factura (id_factura, id_servicio, cantidad, precio_unitario, subtotal, estado_taller)
        VALUES (%s, %s, 1, %s, %s, 'pendiente')
    """, (factura_id, id_servicio, precio, precio))
    conn.commit()
    conn.close()

    flash("✅ Servicio agregado a la factura correctamente", "success")
    return redirect(url_for("routes.ver_factura", id_factura=factura_id))


# --------------------------
# PETICIONES DE SERVICIO (TALLER)
# --------------------------
@routes.route("/taller/peticiones_servicio")
def ver_peticiones_servicio():
    if "usuario" not in session or session["usuario"]["rol"] != "taller":
        flash("Acceso no autorizado ❌", "danger")
        return redirect(url_for("routes.login"))

    id_taller = session["usuario"]["numdocumento"]
    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)

    # Consultar todos los servicios pendientes asociados a este taller
    cursor.execute("""
        SELECT d.id_detalle,
               f.id_factura,
               u.nombre_usu AS cliente,
               s.tipo_servicio AS servicio,
               d.precio_unitario,
               d.subtotal,
               d.estado_taller
        FROM detalle_factura d
        JOIN factura f ON d.id_factura = f.id_factura
        JOIN usuario u ON f.id_cliente = u.numdocumento
        JOIN servicio s ON d.id_servicio = s.id_servicio
        WHERE s.id_usutaller = %s
        ORDER BY f.fecha_emision DESC
    """, (id_taller,))
    
    peticiones = cursor.fetchall()
    conn.close()
    return render_template("peticiones_servicio_taller.html", peticiones=peticiones)


# --------------------------
# ACEPTAR O RECHAZAR PETICIÓN
# --------------------------
@routes.route("/taller/peticiones_servicio/<int:id_detalle>/actualizar", methods=["POST"])
def actualizar_peticion_servicio(id_detalle):
    if "usuario" not in session or session["usuario"]["rol"] != "taller":
        flash("Acceso no autorizado ❌", "danger")
        return redirect(url_for("routes.login"))

    estado = request.form.get("estado")  # 'aprobada' o 'rechazada'
    if estado not in ["aprobada", "rechazada"]:
        flash("Estado inválido ❌", "danger")
        return redirect(url_for("routes.ver_peticiones_servicio"))

    conn = conectar_db()
    cursor = conn.cursor()

    # Actualizar estado en detalle_factura
    cursor.execute("""
        UPDATE detalle_factura
        SET estado_taller = %s
        WHERE id_detalle = %s
    """, (estado, id_detalle))

    conn.commit()
    conn.close()

    flash(f"Petición {estado} con éxito ✅", "success")
    return redirect(url_for("routes.ver_peticiones_servicio"))

# --------------------------
# SOLICITUD DE PROVEEDOR (TALLER)
# --------------------------
@routes.route("/taller/solicitud_proveedor", methods=["GET", "POST"])
def solicitud_proveedor():
    if "usuario" not in session or session["usuario"]["rol"] != "taller":
        flash("Acceso no autorizado ❌", "danger")
        return redirect(url_for("routes.login"))

    if request.method == "POST":
        id_taller = session["usuario"]["numdocumento"]
        nombre = request.form["nombre"]
        telefono = request.form["telefono"]
        correo = request.form["correo"]
        direccion = request.form["direccion"]

        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO solicitud_proveedor (id_taller, nombre_proveedor, telefono, correo, direccion)
            VALUES (%s, %s, %s, %s, %s)
        """, (id_taller, nombre, telefono, correo, direccion))
        conn.commit()
        conn.close()

        flash("Solicitud de proveedor enviada ✅", "success")
        return redirect(url_for("routes.perfil_taller"))  # 👈 aquí el cambio

    return render_template("taller/solicitud_proveedor.html")


@routes.route("/admin/solicitudes_proveedor")
def admin_solicitudes_proveedor():
    if "usuario" not in session or session["usuario"]["rol"] != "admin":
        flash("Acceso no autorizado ❌", "danger")
        return redirect(url_for("routes.login_admin"))

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT sp.*, u.nombre_usu AS nombre_taller, u.correoElectronico AS correo_taller
        FROM solicitud_proveedor sp
        JOIN usuario u ON sp.id_taller = u.numdocumento
        WHERE sp.estado = 'pendiente'
    """)
    solicitudes = cursor.fetchall()
    conn.close()

    return render_template("admin_solicitudes_proveedor.html", solicitudes=solicitudes)

@routes.route("/admin/solicitud_proveedor/<int:id_solicitud>/<string:accion>")
def admin_resolver_solicitud_proveedor(id_solicitud, accion):
    # Validar acceso de administrador
    if "usuario" not in session or session["usuario"]["rol"] != "admin":
        flash("Acceso no autorizado ❌", "danger")
        return redirect(url_for("routes.login_admin"))

    conn = conectar_db()
    cursor = conn.cursor()

    if accion == "aprobar":
        cursor.execute("""
            UPDATE solicitud_proveedor 
            SET estado = 'aprobado'
            WHERE id_solicitud = %s
        """, (id_solicitud,))
        flash("Proveedor aprobado ✅", "success")

    elif accion == "rechazar":
        cursor.execute("""
            UPDATE solicitud_proveedor 
            SET estado = 'rechazado'
            WHERE id_solicitud = %s
        """, (id_solicitud,))
        flash("Solicitud rechazada ❌", "warning")

    else:
        flash("Acción inválida ❌", "danger")

    conn.commit()
    conn.close()

    return redirect(url_for("routes.admin_solicitudes_proveedor"))

# --------------------------
# PROVEEDOR - VER PEDIDOS
# --------------------------
@routes.route("/proveedor/pedidos")
def proveedor_pedidos():
    if "usuario" not in session or session["usuario"]["rol"] != "proveedor":
        flash("Acceso no autorizado ❌", "danger")
        return redirect(url_for("routes.login"))

    id_proveedor = session["usuario"]["numdocumento"]

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT pp.id_pedido, pp.cantidad, pp.fecha, pp.estado,
               pr.tipo_producto, pr.marca_producto
        FROM pedido_proveedor pp
        JOIN producto pr ON pp.id_producto = pr.id_producto
        WHERE pp.id_proveedor = %s
        ORDER BY pp.fecha DESC
    """, (id_proveedor,))
    pedidos = cursor.fetchall()
    conn.close()

    return render_template("proveedor_pedidos.html", pedidos=pedidos)


# --------------------------
# PROVEEDOR - ACTUALIZAR ESTADO DEL PEDIDO
# --------------------------
@routes.route("/proveedor/pedido/<int:id_pedido>/<string:estado>")
def proveedor_actualizar_pedido(id_pedido, estado):
    if "usuario" not in session or session["usuario"]["rol"] != "proveedor":
        flash("Acceso no autorizado ❌", "danger")
        return redirect(url_for("routes.login"))

    id_proveedor = session["usuario"]["numdocumento"]

    if estado not in ["enviado", "recibido"]:
        flash("Estado inválido ❌", "danger")
        return redirect(url_for("routes.proveedor_pedidos"))

    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE pedido_proveedor
        SET estado = %s
        WHERE id_pedido = %s AND id_proveedor = %s
    """, (estado, id_pedido, id_proveedor))
    conn.commit()
    conn.close()

    flash(f"Pedido #{id_pedido} actualizado a {estado} ✅", "success")
    return redirect(url_for("routes.proveedor_pedidos"))

# --------------------------
# LISTADO DE TALLERES (con reseñas resumidas)
# --------------------------
@routes.route("/comentarios")
def comentarios_listado():
    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)

    talleres, comentarios, todos_talleres = [], [], []
    try:
        # 🔹 Talleres con al menos un comentario
        cursor.execute("""
            SELECT DISTINCT ut.numdocumento AS taller_id, ut.nombre_usu AS taller_nombre
            FROM comentarios c
            JOIN usuario ut ON c.id_usutaller = ut.numdocumento
        """)
        talleres = cursor.fetchall()

        # 🔹 Todos los talleres (para el modal)
        cursor.execute("""
            SELECT u.numdocumento AS taller_id, u.nombre_usu AS taller_nombre
            FROM usuario u
            JOIN rol r ON u.numdocumento = r.numdocumento
            WHERE r.tipoRol = 'taller'
        """)
        todos_talleres = cursor.fetchall()

        # 🔹 Comentarios más recientes
        cursor.execute("""
            SELECT c.comentario, c.calificacion, c.fecha,
                   uc.nombre_usu AS cliente_nombre,
                   ut.nombre_usu AS taller_nombre,
                   ut.numdocumento AS taller_id
            FROM comentarios c
            JOIN usuario uc ON c.id_usucliente = uc.numdocumento
            JOIN usuario ut ON c.id_usutaller = ut.numdocumento
            ORDER BY c.fecha DESC
        """)
        comentarios = cursor.fetchall()

        # 🔹 Normalizar fechas
        for c in comentarios:
            if isinstance(c["fecha"], str):
                try:
                    c["fecha"] = datetime.strptime(c["fecha"], "%Y-%m-%d %H:%M:%S")
                except:
                    pass

    finally:
        cursor.close()
        conn.close()

    return render_template(
        "comentarios.html",
        talleres=talleres,            # Solo con reseñas
        comentarios=comentarios,      # Todas las reseñas
        todos_talleres=todos_talleres # Todos para el modal
    )


# --------------------------
# DETALLE DE TALLER (reseñas específicas)
# --------------------------
@routes.route("/comentarios/<int:id_taller>", methods=["GET", "POST"])
def comentarios_taller(id_taller):
    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)

    taller, comentarios = None, []
    try:
        # 🔹 Obtener datos del taller
        cursor.execute("""
            SELECT u.numdocumento AS taller_id, u.nombre_usu, u.correoElectronico
            FROM usuario u
            JOIN rol r ON u.numdocumento = r.numdocumento
            WHERE u.numdocumento = %s AND r.tipoRol = 'taller'
        """, (id_taller,))
        taller = cursor.fetchone()

        if not taller:
            flash("Taller no encontrado ❌", "danger")
            return redirect(url_for("routes.catalogo"))

        # 🔹 Si es POST y usuario es cliente => insertar comentario
        if request.method == "POST":
            if "usuario" in session and session["usuario"]["rol"] == "cliente":
                comentario = request.form.get("comentario", "").strip()
                try:
                    calificacion = int(request.form.get("calificacion", 0))
                except ValueError:
                    calificacion = 0
                id_cliente = session["usuario"]["numdocumento"]

                if comentario and 1 <= calificacion <= 5:
                    cursor.execute("""
                        INSERT INTO comentarios (comentario, id_usucliente, id_usutaller, calificacion, fecha)
                        VALUES (%s, %s, %s, %s, NOW())
                    """, (comentario, id_cliente, id_taller, calificacion))
                    conn.commit()
                    flash("Comentario publicado ✅", "success")
                else:
                    flash("Comentario o calificación inválida ❌", "danger")
            else:
                flash("Debes iniciar sesión como cliente para comentar ❌", "danger")

        # 🔹 Traer comentarios del taller
        cursor.execute("""
            SELECT c.comentario, c.calificacion, c.fecha,
                   uc.nombre_usu AS cliente_nombre,
                   ut.nombre_usu AS taller_nombre,
                   ut.numdocumento AS taller_id
            FROM comentarios c
            JOIN usuario uc ON c.id_usucliente = uc.numdocumento
            JOIN usuario ut ON c.id_usutaller = ut.numdocumento
            WHERE c.id_usutaller = %s
            ORDER BY c.fecha DESC
        """, (id_taller,))
        comentarios = cursor.fetchall()

        # 🔹 Normalizar fechas
        for c in comentarios:
            if isinstance(c["fecha"], str):
                try:
                    c["fecha"] = datetime.strptime(c["fecha"], "%Y-%m-%d %H:%M:%S")
                except:
                    pass

    finally:
        cursor.close()
        conn.close()

    return render_template("comentarios_taller.html", taller=taller, comentarios=comentarios)


# --------------------------
# NUEVO COMENTARIO (desde modal en listado)
# --------------------------
@routes.route("/comentarios/nuevo", methods=["POST"])
def nuevo_comentario():
    if "usuario" not in session or session["usuario"]["rol"] != "cliente":
        flash("Debes iniciar sesión como cliente para comentar ❌", "danger")
        return redirect(url_for("routes.comentarios_listado"))

    id_taller = request.form.get("id_taller")
    comentario = request.form.get("comentario", "").strip()
    try:
        calificacion = int(request.form.get("calificacion", 0))
    except ValueError:
        calificacion = 0
    id_cliente = session["usuario"]["numdocumento"]

    if not id_taller or not comentario or not (1 <= calificacion <= 5):
        flash("Datos inválidos ❌", "danger")
        return redirect(url_for("routes.comentarios_listado"))

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            INSERT INTO comentarios (comentario, id_usucliente, id_usutaller, calificacion, fecha)
            VALUES (%s, %s, %s, %s, NOW())
        """, (comentario, id_cliente, id_taller, calificacion))
        conn.commit()
        flash("Comentario publicado ✅", "success")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("routes.comentarios_taller", id_taller=id_taller))


# --------------------------
# BUSCADOR (productos, servicios y talleres)
# --------------------------
@routes.route("/buscar", methods=["GET"])
def buscar():
    termino = request.args.get("q", "").strip()

    conn = conectar_db()
    cursor = conn.cursor(dictionary=True)

    # 🔹 Buscar productos
    cursor.execute("""
        SELECT 'producto' AS categoria, p.id_producto AS id, 
               p.tipo_producto AS nombre, p.marca_producto AS detalle, 
               p.precio_producto AS precio
        FROM producto p
        WHERE p.tipo_producto LIKE %s OR p.marca_producto LIKE %s
    """, (f"%{termino}%", f"%{termino}%"))
    productos = cursor.fetchall()

    # 🔹 Buscar servicios
    cursor.execute("""
        SELECT 'servicio' AS categoria, s.id_servicio AS id, 
               s.tipo_servicio AS nombre, NULL AS detalle, s.precio AS precio
        FROM servicio s
        WHERE s.tipo_servicio LIKE %s
    """, (f"%{termino}%",))
    servicios = cursor.fetchall()

    # 🔹 Buscar talleres
    cursor.execute("""
        SELECT 'taller' AS categoria, u.numdocumento AS id, 
               u.nombre_usu AS nombre, u.correoElectronico AS detalle, NULL AS precio
        FROM usuario u
        JOIN rol r ON u.numdocumento = r.numdocumento
        WHERE r.tipoRol = 'taller' 
          AND (u.nombre_usu LIKE %s OR u.correoElectronico LIKE %s)
    """, (f"%{termino}%", f"%{termino}%"))
    talleres = cursor.fetchall()

    resultados = productos + servicios + talleres

    cursor.close()
    conn.close()

    return render_template("buscar.html", termino=termino, resultados=resultados)
