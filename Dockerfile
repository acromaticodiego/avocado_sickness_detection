# 1. Imagen base
FROM python:3.10-slim

# 2. Directorio de trabajo
WORKDIR /app

# 3. Dependencias del sistema (para OpenCV y YOLO)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# 4. Requerimientos de Python (DE LA RAÍZ)
COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar TODO el backend (incluye main.py, static/, modelos…)
COPY yolov8/backend/ /app/

# 6. Exponer puerto
EXPOSE 8000

# 7. Comando de ejecución usando Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]