# Avocato — Clasificación fitosanitaria de aguacates en tiempo real

La inspección fitosanitaria del aguacate se hace a ojo: alguien toma cada fruto, decide si
el daño en la cáscara es roña negra o antracnosis, y lleva la cuenta en papel. Dos
inspectores no coinciden entre sí, y a la sexta hora de turno el mismo inspector no
coincide consigo mismo.

Avocato observa el fruto con una cámara, clasifica cada aguacate como **sano**, **roña
negra** o **antracnosis** en tiempo real, y lleva el conteo por sí solo. Corre a 4.2
fotogramas por segundo en la CPU de un portátil, sin GPU.

![Detección en vivo](docs/deteccion.jpg)

## Qué hace

- **Detección y seguimiento en vivo** sobre el video de la cámara, con la clasificación
  dibujada sobre cada fruto.
- **Conteo automático** por categoría, con distribución de calidad del lote.
- **Análisis de foto individual**: se sube una imagen y se procesa con el mismo modelo.
- **Selección de cámara** y ajuste del umbral de confianza en caliente, sin reiniciar.
- **Usuarios** con registro, ingreso y correo de bienvenida con un PDF de instrucciones.

## Cómo se mantiene honesto el conteo

Detectar la enfermedad es la mitad fácil. El conteo es donde un sistema así se equivoca en
silencio, y aquí se atacan cuatro formas distintas de equivocarse:

| Problema | Qué pasaba | Solución |
|---|---|---|
| Cajas duplicadas | La supresión de no máximos solo compara detecciones de la misma clase, así que un fruto recibía dos cajas y se contaba dos veces | Se fusionan las cajas que comparten 30% de IoU o 50% de contención |
| Cambio de identificador | El rastreador reasignaba el ID del mismo fruto y lo contaba de nuevo | Una caja que absorbe un track ya contado hereda su estado |
| Cambio de fruto | Al poner otro aguacate en la misma posición, el rastreador revivía el track viejo: el fruto nuevo heredaba la etiqueta anterior y no se contaba nunca | Firma de color por track (histograma tono/saturación). El mismo fruto puntúa >0.99 y dos distintos 0.21, con el umbral en 0.70 |
| Detecciones fugaces | Un destello contaba como fruto | Nada se cuenta hasta sostenerse 4 fotogramas seguidos |

Y una decisión de criterio, no de código: **una enfermedad solo se acepta por encima del
70% de confianza**. Por debajo el fruto cuenta como sano, porque condenar un aguacate bueno
le cuesta una venta al productor, mientras que dejar pasar uno dudoso cuesta una segunda
revisión.

## Tecnologías

| Capa | Herramientas |
|---|---|
| Visión | Ultralytics YOLOv8 (modelo propio `aguacatemodel.pt`), ByteTrack con configuración propia, OpenCV, PyTorch (CPU) |
| API | Python 3.10, FastAPI, Uvicorn, Pydantic v2 |
| Frontend | React 18 y Tailwind CSS por CDN, JSX transpilado en el navegador con Babel |
| Datos | SQLite |
| Seguridad | bcrypt para el hasheo de contraseñas |
| Correo | fastapi-mail |
| Despliegue | Docker y Docker Compose, con torch en su variante CPU |

## Estructura

```
yolov8/backend/
├── main.py                   API y endpoints
├── camara.py                 detección, seguimiento, conteo y dibujado
├── control_model.py          contadores por etiqueta
├── base_usuarios.py          acceso a SQLite
├── seguridad.py              hasheo y verificación de contraseñas
├── modelos.py                esquemas de Pydantic
├── email_utils.py            correo de bienvenida
├── bytetrack_avocato.yaml    tracker con memoria corta
└── static/                   principal.html + app.jsx, ingreso y registro
```

## API

| Método | Ruta | Para qué |
|---|---|---|
| GET | `/video_feed` | Stream MJPEG con las detecciones dibujadas |
| GET | `/get_analisis` | Contadores actuales por etiqueta |
| GET | `/camaras` | Cámaras disponibles y la activa |
| POST | `/camaras/seleccionar/{indice}` | Cambia de cámara sin reiniciar |
| POST | `/confianza?valor=` | Ajusta el umbral de detección |
| POST | `/reiniciar_contadores` | Pone el lote a cero |
| POST | `/procesar_imagen` | Analiza una foto subida |
| POST | `/usuarios` · GET `/usuarios` | Registro y listado |
| POST | `/ingreso` | Inicio de sesión |

## Cómo ejecutar

### Opción A — En el equipo (necesaria para la cámara en vivo)

```bash
python -m venv venv
venv\Scripts\activate          # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
cd yolov8/backend
uvicorn main:app --port 8001
```

Abrir http://127.0.0.1:8001/

### Opción B — Docker

```bash
docker compose up --build
```

Abrir http://127.0.0.1:8001/ (el contenedor escucha en el 8000 y se publica en el 8001).
Las carpetas `data/uploads`, `data/result`, `data/recortes` y `data/sqlitebase` se montan
como volúmenes, así que las imágenes procesadas y los usuarios sobreviven a un redespliegue.

**La cámara en vivo no funciona dentro del contenedor en Windows ni macOS**: Docker Desktop
no puede exponer una webcam USB al contenedor. Ahí el contenedor sirve la interfaz, el login
y el análisis de fotos, pero `/video_feed` no encontrará cámara. En Linux se resuelve
descomentando el bloque `devices` de `docker-compose.yml`.

Variable de entorno `CAMERA_INDEX`: fija el índice de cámara de arranque. Sin ella, el
backend autodetecta y prefiere la USB externa
