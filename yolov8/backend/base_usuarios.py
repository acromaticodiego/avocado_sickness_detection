import sqlite3
import os

# --- Configuración de la base de datos ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FOLDER = os.path.join(BASE_DIR, "sqlitebase")
os.makedirs(DB_FOLDER, exist_ok=True)

DB_PATH = os.path.join(DB_FOLDER, "users.db")

# --- Función para conectarse a la DB ---
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- Crear tabla si no existe ---
def crear_tabla():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarioau (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            correo TEXT UNIQUE,
            password TEXT,
            edad INTEGER
        )
    """)
    conn.commit()
    conn.close()

# --- Agregar usuario ---
def agregar_usuario(usuario: dict):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
    "INSERT INTO usuarioau (username, correo, password, edad) VALUES (?, ?, ?, ?)",
    (usuario["nombre"], usuario["email"], usuario["password"], usuario["edad"])  # 👈 usa email
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return {**usuario, "id": user_id}

# --- Obtener todos los usuarios ---
def obtener_usuarios():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarioau")
    usuarios = cursor.fetchall()
    conn.close()
    return [dict(u) for u in usuarios]

# --- Obtener usuario por ID ---
def obtener_usuario_por_id(usuario_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarioau WHERE id = ?", (usuario_id,))
    usuario = cursor.fetchone()
    conn.close()
    return dict(usuario) if usuario else None

# --- Eliminar usuario por ID ---
def eliminar_usuario_por_id(usuario_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM usuarioau WHERE id = ?", (usuario_id,))
    cambios = cursor.rowcount
    conn.commit()
    conn.close()
    return cambios > 0

# --- Aliases para usar en main.py ---
crear_usuario = agregar_usuario
listar_usuarios = obtener_usuarios

# --- Crear la tabla automáticamente al importar el módulo ---
crear_tabla()
