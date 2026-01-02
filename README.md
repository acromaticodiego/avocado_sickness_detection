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
