# S2ST: Real-Time Local AI Translator
*(Speech-to-Speech Translation)*

A professional real-time translation system running **100% Locally**. Converts Spanish speech to English speech with low latency, leveraging the power of your NVIDIA GPU and Meta AI's state-of-the-art models.

## 🌟 Key Features
*   **Total Privacy**: Nothing leaves your machine.
*   **Speech-to-Speech (S2ST)**: Direct translation without slow intermediate steps, using `SeamlessM4T v2`.
*   **Intelligent Voice Detection (VAD)**: Uses **Neural Silero VAD** to detect speech with millimeter precision, ignoring noise and echoes.
*   **Echo Cancellation**: Implements logic to prevent the system from "hearing itself" and entering feedback loops.
*   **Subtitled Video**: Includes a service that injects translated subtitles into a virtual webcam for use in Zoom/Meet.

## 💻 Requirements
*   **GPU**: NVIDIA RTX (Series 30, 40, or 50 recommended) with up-to-date drivers.
*   **OS**: Linux (Ubuntu 22.04+).
*   **RAM**: 16 GB+.
*   **Hardware**: Dedicated Microphone recommended (though PulseAudio loopback is supported).

## 🚀 Quick Start

The project includes a master script that orchestrates everything:

```bash
./start_all.sh
```

This will launch:
1.  **Translation Brain** (`live_translator.py`): Listens to your microphone, translates, and speaks in English.
2.  **Video Service** (`video_service.py`): Creates a virtual camera and overlays subtitles on your video feed.

### Docker Usage (Recommended)
You can also run the entire stack in a container for maximum isolation:

```bash
docker-compose up --build
```
*Note: Configured for NVIDIA Runtime and audio/video device passthrough.*

## 📂 Project Files

| File | Description |
| :--- | :--- |
| **`live_translator.py`** | **The Brain.** Loads the AI model onto the GPU, runs Neural VAD, and processes audio. |
| **`video_service.py`** | Captures your webcam, adds translated subtitles, and emits to a virtual camera (`/dev/video20`). |
| **`start_all.sh`** | Startup script. Sets up the environment and executes everything in the correct order. |
| **`requirements.txt`** | Strict list of Python dependencies (Pointing to PyTorch Nightly for RTX 5060 Ti support). |
| **`CONTEXT.md`** | Master context file describing architecture and rules for AI assistants (Cursor, etc). |

## 🛠️ Installation (If moving the project)

1.  **Install system dependencies:**
    ```bash
    sudo apt-get install python3-pip v4l2loopback-dkms ffmpeg python3-venv
    ```

2.  **Create and activate virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
