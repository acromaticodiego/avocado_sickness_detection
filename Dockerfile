FROM python:3.10-slim

# Salida sin buffer para ver los logs de deteccion en tiempo real, y caches de
# ultralytics/matplotlib en /tmp porque el proceso corre sin privilegios.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    YOLO_CONFIG_DIR=/tmp \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app

# libglib2.0-0 es lo unico que necesita opencv-python-headless; las librerias
# de GUI (libgl1, libsm6, libxext6, libxrender) sobraban porque el backend
# nunca abre una ventana, solo codifica fotogramas a JPEG.
RUN apt-get update && \
    apt-get install -y --no-install-recommends libglib2.0-0 curl && \
    rm -rf /var/lib/apt/lists/*

# Torch CPU antes que el resto: el wheel de PyPI viene con CUDA y pesa unos
# 2.5 GB que aqui no se usan. Al quedar ya instalado, ultralytics lo reutiliza.
#
# Se usa --extra-index-url y no --index-url: este ultimo sustituye a PyPI, y
# entonces las dependencias de torch (typing_extensions y compania) se buscan
# tambien en el indice de PyTorch, que solo publica el codigo fuente y falla al
# compilarlo. El sufijo +cpu es explicito para que pip no dude entre ese wheel
# y el de PyPI con CUDA.
RUN pip install --no-cache-dir \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        torch==2.9.0+cpu torchvision==0.24.0+cpu

COPY requirements.txt ./
# ultralytics depende de opencv-python (la variante con GUI) y pip la instala
# despues de la headless, quedandose ella con el modulo cv2: el contenedor
# entonces arranca pidiendo libxcb.so.1 y muere. Se dejan fuera las dos y se
# reinstala solo la headless, que es la unica que este backend necesita.
RUN pip install --no-cache-dir -r requirements.txt && \
    pip uninstall -y opencv-python opencv-python-headless && \
    pip install --no-cache-dir opencv-python-headless==4.12.0.88

COPY yolov8/backend/ /app/

# Usuario sin privilegios y carpetas de salida creadas por adelantado, para que
# existan aunque no se monte ningun volumen.
RUN useradd --create-home --uid 1000 avocato && \
    mkdir -p /app/uploads /app/result /app/recortes /app/sqlitebase && \
    chown -R avocato:avocato /app
USER avocato

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD curl -fs http://localhost:8000/get_analisis || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
