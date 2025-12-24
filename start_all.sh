#!/bin/bash

# ============================================
# 🎬 START_ALL.SH: Orquesta Video + Traductor
# ============================================

# 0. Limpiar (por si acaso)
pkill -f video_service.py
rm -f subtitle_stream.txt
touch subtitle_stream.txt

# 1. Chequeo de Módulo (Video Loopback)
if [ ! -d "/sys/devices/virtual/video4linux/video20" ]; then
    echo "🔧 [SUDO] Cargando módulo de cámara virtual..."
    sudo modprobe v4l2loopback video_nr=20 card_label="Traductor_IA" exclusive_caps=1
    echo "✅ Módulo cargado."
fi

# 2. Iniciar Servicio de Video (Background)
# Ajusta --camera 0 si tu cámara es otra (/dev/video0)
echo "🎥 Iniciando Servicio de Video (Lip-Sync + Subtítulos)..."
./venv/bin/python3 video_service.py --camera 0 --delay 2.5 --output /dev/video20 &
VIDEO_PID=$!

# Esperar un poco a que el video arranque
sleep 2

# 3. Iniciar Cerebro (Foreground)
echo "🧠 Iniciando Cerebro de Traducción (SeamlessM4T)..."
echo "ℹ️  Para salir presiona Ctrl+C"
./venv/bin/python3 live_translator.py

# 4. Limpieza al salir
echo "🛑 Apagando servicios..."
kill $VIDEO_PID
