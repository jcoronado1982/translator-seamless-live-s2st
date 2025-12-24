# Usamos Ubuntu 22.04 para tener glibc reciente compatible con todo
FROM ubuntu:22.04

# Evitar diálogos interactivos durante la instalación
ENV DEBIAN_FRONTEND=noninteractive

# 1. Instalar Python y dependencias de sistema (Audio/Video/Drivers)
# libgl1/libglib2.0 -> OpenCV
# portaudio19/libasound2 -> Audio/SoundDevice
# pulseaudio-utils -> Para conectarse al audio del host
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3-venv \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    portaudio19-dev \
    libasound2-dev \
    pulseaudio-utils \
    alsa-utils \
    v4l-utils \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Crear symlink de python
RUN ln -s /usr/bin/python3.10 /usr/bin/python

WORKDIR /app

# 2. Instalar dependencias de Python
COPY requirements.txt .

# Primero aseguramos pip reciente
RUN pip3 install --upgrade pip

# Instalamos las dependencies (Esto leerá el --index-url del archivo requirements.txt)
# y bajará la versión Nightly para RTX 5060 Ti
RUN pip3 install --no-cache-dir -r requirements.txt

# 3. Copiar el código
COPY . .

# 4. Ajustar permisos
ENV PYTHONUNBUFFERED=1

# Por defecto corremos el orquestador
CMD ["./start_all.sh"]
