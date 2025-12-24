# S2ST: Real-Time Local AI Translator
*(Speech-to-Speech Translation)*

Sistema profesional de traducción en tiempo real ejecutándose **100% Localmente**. Convierte voz en español a voz en inglés con baja latencia, utilizando la potencia de tu GPU NVIDIA y modelos de última generación de Meta AI.

## 🌟 Características
*   **Privacidad Total**: Nada sale de tu máquina.
*   **Voz a Voz (S2ST)**: Traducción directa sin pasos intermedios lentos, usando `SeamlessM4T v2`.
*   **Detección de Voz Inteligente (VAD)**: Utiliza `Silero VAD` para detectar cuándo hablas con precisión milimétrica.
*   **Video Subtitulado**: Incluye un servicio que inyecta subtítulos en tu cámara web para usarlos en Zoom/Meet.

## 💻 Requisitos
*   **GPU**: NVIDIA RTX (Serie 30, 40 o 50 recomendada) con drivers al día.
*   **OS**: Linux (Ubuntu 22.04+).
*   **RAM**: 16 GB+.

## 🚀 Inicio Rápido

El proyecto incluye un script maestro que orquesta todo:

```bash
./start_all.sh
```

Esto iniciará:
1.  **Cerebro de Traducción** (`live_translator.py`): Escuchará tu micrófono y hablará en inglés.
2.  **Servicio de Video** (`video_service.py`): Creará una cámara virtual y pondrá subtítulos en tu video.

## 📂 Archivos del Proyecto

| Archivo | Descripción |
| :--- | :--- |
| **`live_translator.py`** | El script principal. Carga el modelo de IA en la GPU y procesa el audio. |
| **`video_service.py`** | Captura tu webcam, añade subtítulos traducidos y emite a una cámara virtual. |
| **`start_all.sh`** | Script de arranque. Ejecuta todo en el orden correcto. |
| **`requirements.txt`** | Lista de librerías Python necesarias. |
| **`subtitle_stream.txt`** | Archivo puente donde se escribe el texto traducido para el video. |

## 🛠️ Instalación (Si mueves el proyecto)

1.  **Instalar dependencias de sistema:**
    ```bash
    sudo apt-get install python3-pip v4l2loopback-dkms ffmpeg
    ```

2.  **Instalar dependencias de Python:**
    ```bash
    pip install -r requirements.txt
    ```
