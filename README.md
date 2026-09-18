🍃 Sistema de Visión Artificial para Clasificación de Aguacates en Tiempo Real

Este proyecto implementa un sistema completo de visión artificial para la detección, clasificación y conteo de aguacates en tiempo real, utilizando YOLO y una arquitectura backend moderna basada en FastAPI.

El sistema se conecta a una cámara en vivo, realiza detección y tracking de aguacates y clasifica cada fruto en una de las siguientes categorías:

✅ Bueno

⚫ Roña negra

🍂 Antracnosis

Los resultados se visualizan en tiempo real a través de una interfaz web, donde también se muestran los contadores dinámicos por cada tipo de clasificación.

🚀 Funcionalidades principales

📷 Detección en tiempo real usando cámara y modelo YOLO

🎯 Clasificación automática de aguacates según su estado fitosanitario

🔄 Tracking para evitar conteos duplicados

📊 Contadores en vivo (totales, buenos, roña negra y antracnosis)

🌐 Interfaz web moderna e intuitiva

👤 Sistema de usuarios con:

Registro

Login

Perfil de usuario

📧 Correo de bienvenida automático al registrarse, incluyendo:

Mensaje de bienvenida

PDF con instrucciones de uso del sistema

🖼️ Procesamiento de imágenes cargadas manualmente

⚙️ Backend robusto y escalable con FastAPI

🧠 Arquitectura y tecnologías

Lenguaje: Python 3.10

Framework backend: FastAPI

Modelo de visión artificial: YOLO

Streaming de video: OpenCV + StreamingResponse

Frontend: HTML, CSS y JavaScript (servido como archivos estáticos)

Gestión de usuarios: Base de datos + Pydantic

Entorno virtual: Python venv

Arquitectura modular: separación clara entre cámara, modelo, control y API

🖥️ Flujo del sistema

El usuario se registra o inicia sesión desde la web

Al registrarse, recibe un correo de bienvenida con un PDF explicativo

Tras el login, accede a la interfaz principal

La cámara se activa y comienza la detección en tiempo real

El sistema:

Detecta

Clasifica

Rastrea

Cuenta los aguacates automáticamente

Los resultados se muestran en vivo en la web

## 🚀 Cómo ejecutar

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

Las carpetas `data/uploads`, `data/result`, `data/recortes` y `data/sqlitebase` se montan como volúmenes, así que las imágenes procesadas y los usuarios sobreviven a un redespliegue.

**La cámara en vivo no funciona dentro del contenedor en Windows ni macOS**: Docker Desktop no puede exponer una webcam USB al contenedor. Ahí el contenedor sirve la interfaz, el login y el análisis de fotos, pero `/video_feed` no encontrará cámara. En Linux se resuelve descomentando el bloque `devices` de `docker-compose.yml`. Para el streaming en vivo en Windows, usar la opción A.

### Variables de entorno

| Variable | Por defecto | Para qué sirve |
|---|---|---|
| `CAMERA_INDEX` | autodetección (prefiere la USB externa) | Fija el índice de cámara con el que arranca el backend |

## ⚠️ Limitaciones conocidas

- **El modelo está entrenado a 640 px** y a esa resolución devuelve cajas que a veces cubren solo parte del fruto. El backend las expande al contorno real del aguacate segmentándolo del fondo claro; es una mitigación geométrica, no un arreglo del modelo. La solución de fondo es reentrenar con anotaciones mejores.
- **El ajuste de caja depende del contraste con el fondo.** Sobre una bandeja clara funciona; sobre un fondo oscuro o abarrotado cae al comportamiento del modelo.
- **Una enfermedad solo se acepta por encima del 70% de confianza.** Por debajo, el fruto se cuenta como bueno: es preferible dejar pasar un aguacate dudoso que condenar uno sano.
- **Aún no hay métricas publicadas** (mAP, precisión y exhaustividad por clase). Los porcentajes que muestra la interfaz son la confianza de cada detección, no el acierto del modelo.
