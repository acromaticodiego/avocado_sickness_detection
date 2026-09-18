import os
import time
import cv2
import uuid
import numpy as np
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

# Tracker propio: mismo ByteTrack pero con memoria corta, para que al cambiar
# de aguacate no se reviva el track anterior. Si falta, se usa el de ultralytics.
TRACKER_PATH = os.path.join(BASE_DIR, "bytetrack_avocato.yaml")
if not os.path.exists(TRACKER_PATH):
    TRACKER_PATH = "bytetrack.yaml"

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

# -------------------------
# ESTILO Y REGLAS DE LAS DETECCIONES
# -------------------------
# Colores en BGR alineados con la paleta del panel web
COLORES_CLASE = {
    "sano": (94, 197, 34),          # verde
    "sarna-negra": (11, 158, 245),  # ambar
    "antracnosis": (68, 68, 239),   # rojo
}
COLOR_PENDIENTE = (170, 170, 170)   # gris para detecciones aun sin confirmar

NOMBRES_VISIBLES = {
    "sano": "Sano",
    "sarna-negra": "Sarna Negra",
    "antracnosis": "Antracnosis",
}

# Una enfermedad solo se acepta si el modelo la reporta con al menos esta
# confianza. Por debajo del umbral el fruto se clasifica como sano, para no
# marcar como enfermo un aguacate sobre el que el modelo no esta seguro.
UMBRAL_ENFERMEDAD = 0.70
CLASES_ENFERMEDAD = ("sarna-negra", "antracnosis")

# Dos cajas se consideran el mismo fruto si comparten esta fraccion de area.
# La contencion (interseccion sobre la caja mas pequena) atrapa el caso tipico
# del tracker: una caja grande y otra mas pequena encima del mismo aguacate.
UMBRAL_IOU_DUPLICADO = 0.30
UMBRAL_CONTENCION_DUPLICADO = 0.50


def clasificar_deteccion(label: str, conf: float, umbral: float = UMBRAL_ENFERMEDAD) -> str:
    """Devuelve la clase efectiva aplicando el umbral de enfermedad."""
    if label in CLASES_ENFERMEDAD and conf < umbral:
        return "sano"
    return label


def color_de_clase(label: str):
    return COLORES_CLASE.get(label, COLOR_PENDIENTE)


def nombre_visible(label: str) -> str:
    return NOMBRES_VISIBLES.get(label, label.replace("-", " ").title())


def _recortar(valor, minimo, maximo):
    return max(minimo, min(valor, maximo))


def dibujar_caja(img, x1, y1, x2, y2, color, grosor=2):
    """Caja de esquinas: marco tenue con refuerzos en las cuatro esquinas."""
    alto, ancho = img.shape[:2]
    x1 = _recortar(x1, 0, ancho - 1)
    x2 = _recortar(x2, 0, ancho - 1)
    y1 = _recortar(y1, 0, alto - 1)
    y2 = _recortar(y2, 0, alto - 1)
    if x2 <= x1 or y2 <= y1:
        return

    cv2.rectangle(img, (x1, y1), (x2, y2), color, 1, cv2.LINE_AA)

    largo = max(10, int(min(x2 - x1, y2 - y1) * 0.20))
    grosor_esquina = grosor + 1
    for cx, dx in ((x1, 1), (x2, -1)):
        for cy, dy in ((y1, 1), (y2, -1)):
            cv2.line(img, (cx, cy), (cx + dx * largo, cy), color, grosor_esquina, cv2.LINE_AA)
            cv2.line(img, (cx, cy), (cx, cy + dy * largo), color, grosor_esquina, cv2.LINE_AA)


# Similitud de histograma por debajo de la cual se considera que el fruto que
# ocupa un track ya no es el mismo. Medido sobre la camara real: fotogramas del
# mismo aguacate dan >=0.99 y dos aguacates distintos ~0.21, asi que 0.70 separa
# ambos casos con mucho margen.
UMBRAL_SIMILITUD_FRUTO = 0.70


def firma_color(img, caja, bins=(8, 8)):
    """Histograma tono/saturacion del interior de la caja: identifica al fruto."""
    x1, y1, x2, y2 = caja
    w, h = x2 - x1, y2 - y1
    if w <= 0 or h <= 0:
        return None

    # Se recorta un 20% por lado para que el fondo no entre en el histograma
    mx, my = int(w * 0.20), int(h * 0.20)
    roi = img[y1 + my:y2 - my, x1 + mx:x2 - mx]
    if roi.size == 0:
        return None

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, list(bins), [0, 180, 0, 256])
    cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)
    return hist


def similitud_firmas(firma_a, firma_b):
    if firma_a is None or firma_b is None:
        return 1.0
    return float(cv2.compareHist(firma_a, firma_b, cv2.HISTCMP_CORREL))


def ajustar_caja_al_objeto(img, caja, margen=0.75, max_crecimiento=6.0):
    """
    Expande la caja del modelo hasta el contorno real del fruto.

    El modelo esta entrenado a 640 px y suele devolver una caja que solo cubre
    una parte del aguacate. Aqui se busca el contorno del fruto dentro de una
    region ampliada y se devuelve la union de ambas cajas, de modo que la caja
    nunca se hace mas pequena que la que dio el modelo. Si la segmentacion no
    es fiable (se come el fondo, crece demasiado, no encuentra contorno) se
    devuelve la caja original sin tocar.
    """
    x1, y1, x2, y2 = caja
    alto, ancho = img.shape[:2]
    w, h = x2 - x1, y2 - y1
    if w <= 0 or h <= 0:
        return caja

    # Region de busqueda: la caja del modelo ampliada por el margen
    rx1 = _recortar(int(x1 - w * margen), 0, ancho - 1)
    ry1 = _recortar(int(y1 - h * margen), 0, alto - 1)
    rx2 = _recortar(int(x2 + w * margen), 1, ancho)
    ry2 = _recortar(int(y2 + h * margen), 1, alto)
    roi = img[ry1:ry2, rx1:rx2]
    if roi.size == 0:
        return caja

    # El fruto destaca del fondo claro por saturacion (verde) o por ser oscuro
    # (zonas enfermas); se combinan ambos criterios con umbral automatico.
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    _, mascara_sat = cv2.threshold(hsv[:, :, 1], 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    _, mascara_val = cv2.threshold(hsv[:, :, 2], 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    mascara = cv2.bitwise_or(mascara_sat, mascara_val)

    nucleo = np.ones((5, 5), np.uint8)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, nucleo, iterations=2)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, nucleo, iterations=1)

    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contornos:
        return caja

    # Solo vale el contorno que contiene el centro de la caja del modelo
    cx = (x1 + x2) // 2 - rx1
    cy = (y1 + y2) // 2 - ry1
    candidatos = [c for c in contornos if cv2.pointPolygonTest(c, (cx, cy), False) >= 0]
    if not candidatos:
        return caja

    bx, by, bw, bh = cv2.boundingRect(max(candidatos, key=cv2.contourArea))

    # Salvaguardas: ni crecer sin control ni tragarse el fondo entero
    if bw * bh > (w * h) * max_crecimiento:
        return caja
    if bw * bh > 0.85 * roi.shape[0] * roi.shape[1]:
        return caja

    return (
        min(x1, rx1 + bx),
        min(y1, ry1 + by),
        max(x2, rx1 + bx + bw),
        max(y2, ry1 + by + bh),
    )


def _solape(caja_a, caja_b):
    """Devuelve (IoU, interseccion sobre el area de la caja mas pequena)."""
    ax1, ay1, ax2, ay2 = caja_a
    bx1, by1, bx2, by2 = caja_b

    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0, 0.0

    area_a = max(1, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(1, (bx2 - bx1) * (by2 - by1))
    iou = inter / float(area_a + area_b - inter)
    contencion = inter / float(min(area_a, area_b))
    return iou, contencion


def suprimir_solapadas(detecciones, umbral_iou=UMBRAL_IOU_DUPLICADO,
                       umbral_contencion=UMBRAL_CONTENCION_DUPLICADO):
    """
    Deja una sola caja por fruto. El tracker y el NMS por clase pueden emitir
    dos cajas sobre el mismo aguacate (por ejemplo cuando cambia el ID); aqui
    se conserva la de mayor confianza y las demas quedan registradas en
    "absorbidas" para poder heredar su identidad y no contar el fruto dos veces.
    """
    ordenadas = sorted(detecciones, key=lambda d: d.get("conf", 0.0), reverse=True)
    conservadas = []

    for det in ordenadas:
        duplicada_de = None
        for conservada in conservadas:
            iou, contencion = _solape(det["caja"], conservada["caja"])
            if iou >= umbral_iou or contencion >= umbral_contencion:
                det["solape"] = (iou, contencion)
                duplicada_de = conservada
                break

        if duplicada_de is None:
            det["absorbidas"] = []
            conservadas.append(det)
        else:
            duplicada_de["absorbidas"].append(det)

    return conservadas


def _se_solapan(rect_a, rect_b):
    ax1, ay1, ax2, ay2 = rect_a
    bx1, by1, bx2, by2 = rect_b
    return not (ax2 <= bx1 or bx2 <= ax1 or ay2 <= by1 or by2 <= ay1)


def dibujar_etiqueta(img, x, y, texto, color, escala=0.5, ocupados=None):
    """Etiqueta tipo chip: fondo del color de la clase y texto oscuro encima.

    Si se pasa "ocupados" (lista de rectangulos ya dibujados en el fotograma),
    la etiqueta se desplaza hasta encontrar un hueco libre en vez de escribirse
    encima de otra.
    """
    fuente = cv2.FONT_HERSHEY_DUPLEX
    (ancho_texto, alto_texto), _ = cv2.getTextSize(texto, fuente, escala, 1)
    pad_x, pad_y = 8, 6
    chip_w = ancho_texto + pad_x * 2
    chip_h = alto_texto + pad_y * 2

    alto, ancho = img.shape[:2]
    if chip_w > ancho or chip_h > alto:
        return

    cx = _recortar(x, 0, ancho - chip_w)

    # Posiciones candidatas: encima de la caja, dentro de ella, y luego
    # desplazada hacia abajo hasta encontrar un hueco sin etiquetas.
    candidatas = [y - chip_h - 4, y + 4]
    candidatas += [y + 4 + (chip_h + 4) * i for i in range(1, 5)]

    cy = _recortar(candidatas[0], 0, alto - chip_h)
    for candidata in candidatas:
        posible = _recortar(candidata, 0, alto - chip_h)
        rect = (cx, posible, cx + chip_w, posible + chip_h)
        if not ocupados or not any(_se_solapan(rect, otro) for otro in ocupados):
            cy = posible
            break

    if ocupados is not None:
        ocupados.append((cx, cy, cx + chip_w, cy + chip_h))

    region = img[cy:cy + chip_h, cx:cx + chip_w]
    fondo = region.copy()
    fondo[:] = color
    cv2.addWeighted(fondo, 0.85, region, 0.15, 0, region)

    cv2.putText(
        img, texto, (cx + pad_x, cy + pad_y + alto_texto - 1),
        fuente, escala, (20, 20, 20), 1, cv2.LINE_AA
    )


def dibujar_deteccion(img, caja, texto, color, grosor=2, escala=0.5, ocupados=None):
    x1, y1, x2, y2 = caja
    dibujar_caja(img, x1, y1, x2, y2, color, grosor)
    dibujar_etiqueta(img, x1, y1, texto, color, escala, ocupados)


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

    results = model(img, imgsz=640, conf=0.6, iou=0.6, agnostic_nms=True, verbose=False)
    img_draw = img.copy()

    # El trazo se escala con el tamano de la imagen para que se vea igual de
    # nitido en una foto de 480 px que en una de 3000 px.
    escala_texto = _recortar(img.shape[1] / 1200, 0.45, 1.1)
    grosor_caja = max(2, int(img.shape[1] / 500))

    detecciones = []
    for box in results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        conf = float(box.conf[0])
        detecciones.append({
            "conf": conf,
            # La caja se ajusta al contorno real para que abarque todo el fruto
            "caja": ajustar_caja_al_objeto(img, (x1, y1, x2, y2)),
            "label": clasificar_deteccion(model.names[int(box.cls[0])], conf),
        })

    etiquetas_ocupadas = []
    for det in suprimir_solapadas(detecciones):
        x1, y1, x2, y2 = det["caja"]
        label = det["label"]

        # Guardar recorte individual
        crop = img[y1:y2, x1:x2]
        if crop.size:
            crop_filename = f"{uuid.uuid4().hex}_{label}.jpg"
            cv2.imwrite(os.path.join(RECORTES_DIR, crop_filename), crop)

        dibujar_deteccion(
            img_draw, det["caja"],
            f"{nombre_visible(label)}  {det['conf']:.0%}",
            color_de_clase(label), grosor_caja, escala_texto,
            ocupados=etiquetas_ocupadas
        )

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
        self.umbral_enfermedad = UMBRAL_ENFERMEDAD  # Por debajo de esto, la enfermedad se cuenta como sano
        self.solapes_reportados = set()  # Para no repetir el log de duplicados en cada fotograma
        self.ajustar_cajas = True  # Ajustar la caja del modelo al contorno real del fruto
        self.firmas: Dict[int, object] = {}  # Histograma de color por track, para detectar cambios de fruto
        self.desajustes: Dict[int, int] = {}  # Fotogramas seguidos con firma distinta
        self.umbral_similitud = UMBRAL_SIMILITUD_FRUTO
        self.min_frames_cambio = 2  # Fotogramas seguidos distintos para dar por cambiado el fruto

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
        self.solapes_reportados.clear()
        self.firmas.clear()
        self.desajustes.clear()
        print("✔️ Contadores y estados de seguimiento reiniciados a 0.")

    def generar_frames(self) -> Generator[bytes, None, None]:
        indice_activo = self.camara_index
        print(f"Iniciando captura en vivo desde cámara índice {indice_activo}")
        print(
            f"[deteccion] confianza>={self.confianza:.2f} | "
            f"enfermedad>={self.umbral_enfermedad:.2f} | "
            f"duplicados IoU>={UMBRAL_IOU_DUPLICADO:.2f} o contencion>={UMBRAL_CONTENCION_DUPLICADO:.2f} | "
            f"cambio de fruto si similitud<{self.umbral_similitud:.2f} | tracker {os.path.basename(TRACKER_PATH)}"
        )

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
                    tracker=TRACKER_PATH,
                    agnostic_nms=True,
                    verbose=False
                )

                frame_draw = frame.copy()
                boxes = results[0].boxes if len(results) > 0 else None
                etiquetas_ocupadas = []

                if boxes is not None and len(boxes) > 0 and boxes.id is not None:
                    track_ids = boxes.id.int().cpu().tolist()
                    class_ids = boxes.cls.int().cpu().tolist()
                    confs = boxes.conf.cpu().tolist()
                    xyxys = boxes.xyxy.int().cpu().tolist()

                    detecciones = []
                    for track_id, cls_id, conf, (x1, y1, x2, y2) in zip(track_ids, class_ids, confs, xyxys):
                        # Filtro de tamaño: descartar cajas diminutas (ruido) o gigantescas que cubren toda la vista
                        w = x2 - x1
                        h = y2 - y1
                        if w < 35 or h < 35 or (w > 610 and h > 450):
                            continue

                        detecciones.append({
                            "track_id": track_id,
                            "conf": conf,
                            # La caja se ajusta al contorno real del fruto
                            "caja": ajustar_caja_al_objeto(frame, (x1, y1, x2, y2))
                            if self.ajustar_cajas else (x1, y1, x2, y2),
                            # Umbral de enfermedad: una lesion solo se acepta si el
                            # modelo esta seguro; si no, el fruto se toma como sano.
                            "label": clasificar_deteccion(
                                model.names[cls_id], conf, self.umbral_enfermedad
                            ),
                        })

                    # Una sola caja por fruto: se descartan las cajas solapadas
                    for det in suprimir_solapadas(detecciones):
                        track_id = det["track_id"]
                        conf = det["conf"]
                        label = det["label"]

                        # Cambio de fruto: el tracker reutiliza el ID cuando aparece
                        # otro aguacate en la misma posicion. Si el color del fruto
                        # deja de parecerse al que ocupaba el track, se reinicia su
                        # estado para que la unidad nueva se cuente y se etiquete
                        # por si misma en vez de heredar la etiqueta anterior.
                        cambio_de_fruto = False
                        firma = firma_color(frame, det["caja"])
                        firma_previa = self.firmas.get(track_id)

                        if firma is not None and firma_previa is not None:
                            similitud = similitud_firmas(firma, firma_previa)
                            if similitud < self.umbral_similitud:
                                self.desajustes[track_id] = self.desajustes.get(track_id, 0) + 1
                                if self.desajustes[track_id] >= self.min_frames_cambio:
                                    cambio_de_fruto = True
                                    self.desajustes[track_id] = 0
                                    self.aguacate_status.pop(track_id, None)
                                    self.track_frames[track_id] = 0
                                    self.firmas[track_id] = firma
                                    print(
                                        f"[deteccion] fruto distinto en #{track_id} "
                                        f"(similitud {similitud:.2f}): se cuenta como unidad nueva"
                                    )
                            else:
                                self.desajustes[track_id] = 0
                                # Mezcla suave: absorbe cambios de luz sin perder la identidad
                                self.firmas[track_id] = 0.8 * firma_previa + 0.2 * firma
                        elif firma is not None:
                            self.firmas[track_id] = firma

                        # Registro de duplicados absorbidos, una vez por par
                        for absorbida in det["absorbidas"]:
                            par = (absorbida["track_id"], track_id)
                            if par not in self.solapes_reportados:
                                if len(self.solapes_reportados) > 300:
                                    self.solapes_reportados.clear()
                                self.solapes_reportados.add(par)
                                iou, contencion = absorbida.get("solape", (0.0, 0.0))
                                print(
                                    f"[deteccion] caja duplicada: #{absorbida['track_id']} "
                                    f"absorbida por #{track_id} "
                                    f"(IoU {iou:.2f}, contencion {contencion:.2f})"
                                )

                        # Herencia de identidad: si esta caja absorbio a otro track
                        # que ya estaba contado, es el mismo aguacate con un ID
                        # nuevo, asi que hereda su estado en vez de contarse aparte.
                        if not cambio_de_fruto and track_id not in self.aguacate_status:
                            for absorbida in det["absorbidas"]:
                                anterior = absorbida["track_id"]
                                if anterior in self.aguacate_status:
                                    self.aguacate_status[track_id] = self.aguacate_status.pop(anterior)
                                    self.track_frames[track_id] = max(
                                        self.track_frames.get(track_id, 0),
                                        self.min_frames_confirmacion
                                    )
                                    self.track_frames.pop(anterior, None)
                                    break

                        # Filtro de persistencia temporal: solo contar si aparece al menos N fotogramas continuos
                        self.track_frames[track_id] = self.track_frames.get(track_id, 0) + 1
                        confirmado = self.track_frames[track_id] >= self.min_frames_confirmacion

                        if confirmado:
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

                        # Dibujar caja y etiqueta. Mientras la deteccion no se
                        # confirma se muestra en gris como "Analizando".
                        if confirmado:
                            p_label = self.aguacate_status.get(track_id, label)
                            color = color_de_clase(p_label)
                            texto = f"#{track_id}  {nombre_visible(p_label)}  {conf:.0%}"
                        else:
                            color = COLOR_PENDIENTE
                            texto = f"#{track_id}  Analizando"

                        dibujar_deteccion(
                            frame_draw, det["caja"], texto, color,
                            ocupados=etiquetas_ocupadas
                        )

                # Limpieza periódica para evitar fuga de memoria si hay muchos IDs antiguos
                if len(self.aguacate_status) > 500:
                    ultimos_ids = list(self.aguacate_status.keys())[-200:]
                    self.aguacate_status = {k: self.aguacate_status[k] for k in ultimos_ids}
                    self.track_frames = {k: self.track_frames[k] for k in ultimos_ids if k in self.track_frames}
                    self.firmas = {k: self.firmas[k] for k in ultimos_ids if k in self.firmas}
                    self.desajustes = {k: self.desajustes[k] for k in ultimos_ids if k in self.desajustes}

                ret, buffer = cv2.imencode(".jpg", frame_draw)
                if not ret:
                    break

                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" +
                       buffer.tobytes() + b"\r\n")
        finally:
            cap.release()
            print(f"Cámara {indice_activo} liberada correctamente.")
        print("Stream finalizado.")
