import os
import time
import cv2
import uuid
from fastapi import HTTPException
from typing import Generator, Dict
from ultralytics import YOLO

# -------------------------
# RUTAS
# -------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
RESULTS_DIR = os.path.join(BASE_DIR, "result")
RECORTES_DIR = os.path.join(BASE_DIR, "recortes")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(RECORTES_DIR, exist_ok=True)

# -------------------------
# CARGAR MODELO UNA SOLA VEZ
# -------------------------
print("Cargando modelo YOLOv8...")
try:
    model_path = os.path.join(BASE_DIR, "aguacatemodel.pt")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"No se encontró el modelo en {model_path}")
    model = YOLO(model_path)
    print("Modelo cargado con éxito ✔️")
except Exception as e:
    print(f"ERROR al cargar modelo YOLO: {e}")
    model = None

def buscar_camara(max_indices=6):
    """
    Busca automáticamente la primera cámara funcional:
    0 → 1 → 2 → ... (como COM0, COM1)
    """
    for i in range(max_indices):
        cap = cv2.VideoCapture(i)
        time.sleep(0.1)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                cap.release()
                print(f"✔️ Cámara encontrada en índice {i}")
                return i
        cap.release()

    print("❌ No se encontró ninguna cámara disponible.")
    return None

def procesar_imagen(filename: str):
    """
    Procesa una imagen subida:
    - Dibuja detecciones
    - Guarda recortes individuales
    - Guarda imagen resultante
    """
    if model is None:
        raise RuntimeError("Modelo YOLO no disponible.")

    filepath = os.path.join(UPLOADS_DIR, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"No se encontró la imagen {filepath}")

    img = cv2.imread(filepath)

    results = model(img, imgsz=288, conf=0.6, iou=0.6)
    img_draw = results[0].plot()

    # Guardar recortes
    for box in results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        label = model.names[int(box.cls[0])]
        crop = img[y1:y2, x1:x2]
        crop_filename = f"{uuid.uuid4().hex}_{label}.jpg"
        cv2.imwrite(os.path.join(RECORTES_DIR, crop_filename), crop)

    result_filename = f"detect_{filename}"
    cv2.imwrite(os.path.join(RESULTS_DIR, result_filename), img_draw)

    return result_filename


class CamaraManager:
    def __init__(self, control_model, max_try_indices: int = 4):
        self.control_model = control_model
        self.aguacate_status: Dict[int, str] = {}
        self.class_priority = {"sano": 0, "sarna-negra": 1, "antracnosis": 2}

        if model is None:
            raise RuntimeError("El modelo YOLO no se pudo cargar.")

        # Buscar cámara automáticamente
        self.camara_index = buscar_camara()
        if self.camara_index is None:
            raise RuntimeError("No se encontró ninguna cámara disponible.")

    def reset_contadores(self):
        if self.control_model:
            self.control_model.reiniciar_contadores()
        self.aguacate_status.clear()

    def generar_frames(self) -> Generator[bytes, None, None]:
        print(f"Iniciando captura en vivo desde cámara {self.camara_index}")

        cap = cv2.VideoCapture(self.camara_index)
        if not cap.isOpened():
            raise HTTPException(status_code=500, detail="No se pudo abrir la cámara.")

        while True:
            cap.set(cv2.CAP_PROP_FPS,200)
            success, frame = cap.read()
            if not success:
                print("Frame no leído, finalizando.")
                break

            results = model.track(
                frame, imgsz=640, conf=0.2, iou=0.45,
                persist=True, tracker="bytetrack.yaml"
            )

            detections = results[0].boxes.data

            for det in detections:
                if det.shape[0] > 5:
                    track_id = int(det[4].item())
                    label_id = int(det[5].item())
                    label = model.names[label_id]

                    if track_id not in self.aguacate_status:
                        if self.control_model:
                            self.control_model.incrementar_contador(label)
                        self.aguacate_status[track_id] = label
                    else:
                        actual = self.aguacate_status[track_id]
                        if self.class_priority.get(label, 0) > self.class_priority.get(actual, 0):
                            if self.control_model:
                                self.control_model.actualizar_contador(actual, label)
                            self.aguacate_status[track_id] = label

            frame_draw = results[0].orig_img

            for det in detections:
                x1, y1, x2, y2 = map(int, det[:4])
                track_id = int(det[4].item())
                p_label = self.aguacate_status.get(track_id, "desconocido")

                color = (0, 255, 0)
                if p_label == "sarna-negra": color = (0, 165, 255)
                if p_label == "antracnosis": color = (0, 0, 255)

                cv2.rectangle(frame_draw, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame_draw, f"ID: {track_id} | {p_label}",
                            (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            ret, buffer = cv2.imencode(".jpg", frame_draw)
            if not ret:
                break

            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" +
                   buffer.tobytes() + b"\r\n")

        cap.release()
        print("Stream finalizado.")
