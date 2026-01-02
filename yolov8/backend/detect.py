import os
import cv2
import uuid
from ultralytics import YOLO

# --- Rutas ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
RESULTS_DIR = os.path.join(BASE_DIR, "result")
RECORTES_DIR = os.path.join(BASE_DIR, "recortes")

# Crear carpetas si no existen
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(RECORTES_DIR, exist_ok=True)

# --- Cargar modelo YOLOv8 ---
print("Cargando modelo YOLOv8 para procesamiento de archivos...")
try:
    model = YOLO(os.path.join(BASE_DIR, "aguacatemodel.pt"))
    print("Modelo de procesamiento cargado con éxito ✅")
except Exception as e:
    print(f"Error al cargar el modelo de YOLO para procesamiento de archivos: {e}")
    model = None

def procesar_imagen(filename: str):
    """
    Procesa una imagen con YOLOv8:
    - Dibuja detecciones en la imagen original
    - Guarda recortes individuales de cada detección
    """
    if model is None:
        raise RuntimeError("El modelo YOLO no está disponible para procesamiento.")

    filepath = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"No se encontró la imagen {filepath}")

    # Lee la imagen del archivo. 'img' es la variable correcta para usar aquí.
    img = cv2.imread(filepath)
    
    # --- CORRECCIÓN CLAVE ---
    # Se utiliza la variable 'img' en lugar de 'frame'.
    # Se añaden los parámetros imgsz=300 y conf=0.7 para mejorar la precisión.
    results = model(img, imgsz=640, conf=0.5, iou=0.5)

    img_draw = results[0].plot()

    for box in results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        label = model.names[int(box.cls[0])]

        crop = img[y1:y2, x1:x2]
        crop_filename = f"{uuid.uuid4().hex}_{label}.jpg"
        crop_path = os.path.join(RECORTES_DIR, crop_filename)
        cv2.imwrite(crop_path, crop)


    result_filename = f"detect_{filename}"
    result_path = os.path.join(RESULTS_DIR, result_filename)
    cv2.imwrite(result_path, img_draw)


    return result_filename


