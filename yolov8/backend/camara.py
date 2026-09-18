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

def detectar_camaras(max_indices=4):
    """
    Detecta qué cámaras funcionales existen en el sistema.
    Usa el backend estándar de OpenCV para evitar excepciones de C++ con DirectShow.
    """
    disponibles = []
    for i in range(max_indices):
        try:
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    disponibles.append(i)
                    print(f"✔️ Cámara detectada en índice {i}")
            cap.release()
        except Exception as e:
            print(f"Aviso al verificar cámara {i}: {e}")

    # Si por alguna razón no detectó nada pero hay hardware, asumir al menos [0, 1]
    if not disponibles:
        disponibles = [0, 1]
    elif len(disponibles) == 1 and 0 in disponibles:
        # Añadir 1 como opción para que el usuario siempre pueda intentar la USB externa
        disponibles.append(1)

    return sorted(list(set(disponibles)))

def buscar_camara(prefer_index=None):
    """
    Selecciona la cámara inicial:
    - Si se especifica CAMERA_INDEX o prefer_index, se usa.
    - Por defecto, si hay una cámara USB (índice 1), se prefiere sobre la integrada (0).
    """
    disponibles = detectar_camaras()

    if prefer_index is None:
        env_index = os.getenv("CAMERA_INDEX")
        if env_index is not None and env_index.strip().isdigit():
            prefer_index = int(env_index)
        else:
            # Preferir índice 1 (cámara USB externa típica)
            prefer_index = 1 if 1 in disponibles else disponibles[0]

    print(f"✔️ Cámara seleccionada para inicio: índice {prefer_index} (Disponibles: {disponibles})")
    return prefer_index, disponibles

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

    results = model(img, imgsz=640, conf=0.6, iou=0.6)
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
    def __init__(self, control_model, camara_index: int = None):
        self.control_model = control_model
        self.aguacate_status: Dict[int, str] = {}
        self.track_frames: Dict[int, int] = {}  # Conteo de fotogramas continuos para validar
        self.class_priority = {"sano": 0, "sarna-negra": 1, "antracnosis": 2}
        self.confianza = 0.55  # 0.55 elimina falsos positivos en baldosas, paredes y sombras
        self.min_frames_confirmacion = 4  # Debe aparecer al menos 4 fotogramas para ser contado

        if model is None:
            raise RuntimeError("El modelo YOLO no se pudo cargar.")

        # Detección inicial
        self.camara_index, self.camaras_disponibles = buscar_camara(prefer_index=camara_index)

    def set_confianza(self, valor: float):
        """
        Permite ajustar la sensibilidad de detección en tiempo real.
        """
        self.confianza = max(0.1, min(0.95, float(valor)))
        print(f"✔️ Umbral de confianza actualizado a {self.confianza:.2f}")

    def get_camaras_disponibles(self):
        lista = list(self.camaras_disponibles)
        if self.camara_index not in lista:
            lista.append(self.camara_index)
        return sorted(list(set(lista)))

    def cambiar_camara(self, nuevo_indice: int) -> bool:
        """
        Permite cambiar la cámara activa dinámicamente.
        """
        print(f"Cambiando cámara a índice {nuevo_indice}...")
        self.camara_index = nuevo_indice
        self.reset_contadores()
        if nuevo_indice not in self.camaras_disponibles:
            self.camaras_disponibles.append(nuevo_indice)
        return True

    def reset_contadores(self):
        if self.control_model:
            self.control_model.reiniciar_contadores()
        self.aguacate_status.clear()
        self.track_frames.clear()
        print("✔️ Contadores y estados de seguimiento reiniciados a 0.")

    def generar_frames(self) -> Generator[bytes, None, None]:
        indice_activo = self.camara_index
        print(f"Iniciando captura en vivo desde cámara índice {indice_activo}")

        cap = cv2.VideoCapture(indice_activo)
        if not cap.isOpened():
            print(f"⚠️ No se pudo abrir cámara {indice_activo}. Probando cámara alternativa...")
            cap.release()
            # Intentar abrir la otra cámara (por ejemplo, índice 0 si falló 1)
            for alt in self.get_camaras_disponibles():
                if alt != indice_activo:
                    cap = cv2.VideoCapture(alt)
                    if cap.isOpened():
                        indice_activo = alt
                        self.camara_index = alt
                        print(f"✔️ Conexión exitosa a cámara de respaldo índice {alt}")
                        break
                    cap.release()

        if not cap.isOpened():
            print("❌ No se pudo abrir ninguna cámara.")
            raise HTTPException(status_code=500, detail="No se pudo abrir ninguna cámara conectada.")

        # Ajuste de resolución
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        try:
            while True:
                if self.camara_index != indice_activo:
                    print(f"Cambio de cámara solicitado ({indice_activo} -> {self.camara_index}). Reiniciando stream...")
                    break

                success, frame = cap.read()
                if not success:
                    print("Frame no leído o cámara desconectada, reintentando...")
                    time.sleep(0.05)
                    success, frame = cap.read()
                    if not success:
                        break

                # Inferencia con tracker utilizando el umbral de confianza ajustado
                results = model.track(
                    frame,
                    imgsz=640,
                    conf=self.confianza,
                    iou=0.45,
                    persist=True,
                    tracker="bytetrack.yaml",
                    verbose=False
                )

                frame_draw = frame.copy()
                boxes = results[0].boxes if len(results) > 0 else None

                if boxes is not None and len(boxes) > 0 and boxes.id is not None:
                    track_ids = boxes.id.int().cpu().tolist()
                    class_ids = boxes.cls.int().cpu().tolist()
                    confs = boxes.conf.cpu().tolist()
                    xyxys = boxes.xyxy.int().cpu().tolist()

                    for track_id, cls_id, conf, (x1, y1, x2, y2) in zip(track_ids, class_ids, confs, xyxys):
                        # Filtro de tamaño: descartar cajas diminutas (ruido) o gigantescas que cubren toda la vista
                        w = x2 - x1
                        h = y2 - y1
                        if w < 35 or h < 35 or (w > 610 and h > 450):
                            continue

                        label = model.names.get(cls_id, str(cls_id)) if hasattr(model, 'names') and isinstance(model.names, dict) else model.names[cls_id]

                        # Filtro de persistencia temporal: solo contar si aparece al menos N fotogramas continuos
                        self.track_frames[track_id] = self.track_frames.get(track_id, 0) + 1

                        if self.track_frames[track_id] >= self.min_frames_confirmacion:
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

                        # Dibujar caja y etiqueta con el valor de confianza real
                        p_label = self.aguacate_status.get(track_id, label)
                        color = (0, 255, 0)  # Verde: sano
                        if p_label == "sarna-negra":
                            color = (0, 165, 255)  # Naranja
                        elif p_label == "antracnosis":
                            color = (0, 0, 255)  # Rojo

                        cv2.rectangle(frame_draw, (x1, y1), (x2, y2), color, 2)
                        cv2.putText(
                            frame_draw,
                            f"ID: {track_id} | {p_label} ({conf:.2f})",
                            (x1, max(18, y1 - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            color,
                            2
                        )

                # Limpieza periódica para evitar fuga de memoria si hay muchos IDs antiguos
                if len(self.aguacate_status) > 500:
                    ultimos_ids = list(self.aguacate_status.keys())[-200:]
                    self.aguacate_status = {k: self.aguacate_status[k] for k in ultimos_ids}
                    self.track_frames = {k: self.track_frames[k] for k in ultimos_ids if k in self.track_frames}

                ret, buffer = cv2.imencode(".jpg", frame_draw)
                if not ret:
                    break

                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" +
                       buffer.tobytes() + b"\r\n")
        finally:
            cap.release()
            print(f"Cámara {indice_activo} liberada correctamente.")
        print("Stream finalizado.")
