# main actualizado para usar el nuevo camara.py sin detect.py
import os
import time
import uuid
import cv2
import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse

from base_usuarios import (
    crear_usuario,
    listar_usuarios,
    obtener_usuario_por_id,
    eliminar_usuario_por_id,
    crear_tabla,
    get_db,
)

from modelos import UsuarioCreate, UsuarioDB
from pydantic import BaseModel

# ⬅ YA NO VIENE DE detect.py
# from detect import procesar_imagen   ❌  BORRADO

# ✔ Ahora viene del camara.py unificado
from camara import CamaraManager, procesar_imagen
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr

from email_utils import enviar_correo_bienvenida
from control_model import ControlModel  # solo importa la clase

# -----------------------------------------
# Crear la app
# -----------------------------------------
app = FastAPI()

# -----------------------------------------
# Instancia global de ControlModel
# -----------------------------------------
control_model = ControlModel()

# -----------------------------------------
# Instancia global de cámara usando ControlModel
# -----------------------------------------
camara_manager = CamaraManager(control_model=control_model)

# -----------------------------------------
# CORS
# -----------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Durante desarrollo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------
# RUTAS Y CARPETAS
# -----------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
RESULTS_DIR = os.path.join(BASE_DIR, "result")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

# Static files
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/result", StaticFiles(directory=RESULTS_DIR), name="result")
app.mount("/static", StaticFiles(directory="static"), name="static")

# -----------------------------------------
# Login model
# -----------------------------------------
class LoginData(BaseModel):
    username: str
    password: str

# -----------------------------------------
# Login Endpoint
# -----------------------------------------
@app.post("/ingreso")
def login_endpoint(data: LoginData):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM usuarioau WHERE username = ? AND password = ?",
        (data.username, data.password)
    )
    usuario = cursor.fetchone()
    conn.close()

    if usuario:
        return {"mensaje": "Login exitoso"}
    else:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

# -----------------------------------------
# Crear usuario
# -----------------------------------------
@app.post("/usuarios", response_model=UsuarioDB)
def crear_usuario_endpoint(usuario: UsuarioCreate, background_tasks: BackgroundTasks):
    try:
        nuevo_usuario = crear_usuario(usuario.dict())

        # Enviar correo en background
        background_tasks.add_task(enviar_correo_bienvenida, nuevo_usuario["email"])

        return nuevo_usuario

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# -----------------------------------------
# Listar usuarios
# -----------------------------------------
@app.get("/usuarios", response_model=list[UsuarioDB])
def listar_usuarios_endpoint():
    return listar_usuarios()

# -----------------------------------------
# STREAMING EN VIVO DESDE LA CÁMARA
# -----------------------------------------
@app.get("/video_feed")
def video_feed():
    try:
        camara_manager.reset_contadores()
        return StreamingResponse(
            camara_manager.generar_frames(),
            media_type="multipart/x-mixed-replace;boundary=frame"
        )

    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException as e:
        print(f"Error al iniciar stream: {e.detail}")
        raise e
    except Exception as e:
        print(f"Error inesperado en video_feed: {e}")
        raise HTTPException(status_code=500, detail="Error interno al iniciar streaming.")

# -----------------------------------------
# Procesar imagen subida (usando procesar_imagen del camara.py)
# -----------------------------------------
@app.post("/procesar_imagen")
async def procesar_imagen_endpoint(file: UploadFile = File(...)):
    filename = f"{uuid.uuid4().hex}.jpg"
    filepath = os.path.join(UPLOADS_DIR, filename)

    # Guardar archivo subido
    with open(filepath, "wb") as f:
        f.write(await file.read())

    # Procesar con la función de camara.py
    result_filename = procesar_imagen(filename)

    return {
        "mensaje": "Procesamiento exitoso",
        "archivo_resultado": f"/result/{result_filename}"
    }

# -----------------------------------------
# Analisis → contadores
# -----------------------------------------
@app.get("/get_analisis")
async def get_analisis():
    return control_model.get_contadores()

@app.get("/contadores")
def contadores_endpoint():
    return control_model.get_contadores()

# -----------------------------------------
# Página principal
# -----------------------------------------
@app.get("/")
async def serve_home():
    return RedirectResponse(url="/static/principal.html")
