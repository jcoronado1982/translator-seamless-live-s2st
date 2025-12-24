# 🧠 TRADUCTOR REAL-TIME S2ST (CONTEXTO MAESTRO)

Este archivo está diseñado para que cualquier IA (Cursor, Antigravity, ChatGPT) entienda **inmediatamente** el estado, la arquitectura y las reglas sagradas del proyecto. **Léelo antes de proponer cambios.**

## 🎯 Objetivo del Proyecto
Sistema de **Traducción de Voz a Voz (S2ST)** de latencia ultra-baja (<3s) utilizando Meta SeamlessM4T v2 Large.
El sistema debe ignorar ruidos no humanos, no escucharse a sí mismo (eco) y superponer subtítulos en video.

## 🏗️ Arquitectura Crítica (NO TOCAR SIN RAZÓN)

1.  **Modelo**: `facebook/seamless-m4t-v2-large` en modo `float16` (o `bfloat16`) sobre CUDA (RTX 5060 Ti).
2.  **Pipeline**:
    *   **NO usamos Cascada** (ASR -> Traducción -> TTS) porque es lenta.
    *   **Usamos S2ST Directo** (`model.generate(generate_speech=True)`). El modelo escupe audio y texto simultáneamente.
3.  **VAD (Voice Activity Detection)**:
    *   ❌ **RMS/Volumen**: PROHIBIDO. Fallaba con ruidos de baño/puertas.
    *   ✅ **Silero Neural VAD**: Usamos `snakers4/silero-vad`. Detecta armónicos humanos. Umbral `0.4`.
    *   **Input**: Si el bloque es grande (100ms), se trocea en chunks de 512 muestras para Silero.
4.  **Cancelación de Eco (Lógica)**:
    *   El micrófono siempre escucha el output de los altavoces.
    *   **Solución**: Al terminar de reproducir audio (`play_audio_cmd`), hacemos un **Queue Flush** (`while not q.empty(): q.get()`) para borrar todo lo que se "escuchó" mientras la IA hablaba. Si quitas esto, la IA entra en bucle infinito hablando consigo misma.

## 📂 Mapa de Archivos Clave

*   **`live_translator.py`**: **EL CEREBRO.** Contiene el loop de audio, Silero VAD, inferencia Seamless y lógica de reproducción.
*   **`start_all.sh`**: **EL LANZADOR.** Prepara el entorno, lanza la cámara virtual y corre el traductor dentro del `venv`.
*   **`video_service.py`**: Proceso separado que lee la webcam, superpone subtítulos desde `subtitle_stream.txt` y lo manda a `/dev/video20` (Virtual Cam).
*   **`requirements.txt`**: Dependencias exactas (PyTorch Nightly para compatibilidad con RTX 5060 Ti `sm_120`).

## ⚡ Reglas de Oro para la IA
1.  **Prioridad de Audio**: Si el modelo genera audio pero falla al decodificar texto, **REPRODUCE EL AUDIO**. No lo bloquees.
2.  **Entorno**: Siempre ejecutar con `./start_all.sh` o el python del venv (`./venv/bin/python3`).
3.  **Hardware**: Asumir siempre **NVIDIA RTX 5060 Ti** (CUDA 12.8+). No degradar a CPU.

## 🐛 Historial de Bugs Solucionados
*   *Bug*: "Me ignora a veces". *Fix*: Se relajó el filtro de texto; si hay audio, se reproduce.
*   *Bug*: "Se repite a sí misma". *Fix*: Implementada purga de cola post-reproducción.
*   *Bug*: "Silero VAD error size". *Fix*: El audio se corta en chunks de 512 muestras exactas antes de entrar a Silero.
