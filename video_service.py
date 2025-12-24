import cv2
import collections
import subprocess
import argparse
import sys
import time
import signal
import os

def check_virtual_camera(device):
    """Verifica si el dispositivo de salida existe."""
    if not os.path.exists(device):
        print(f"❌ Error: No se encuentra el dispositivo virtual {device}")
        print("   Ejecuta: sudo modprobe v4l2loopback video_nr=20 card_label=\"Virtual Cam\" exclusive_caps=1")
        sys.exit(1)

def draw_subtitle_multiline(frame, text, max_width=50):
    if not text: return frame
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.0
    thickness = 2
    h, w, _ = frame.shape
    
    # Wrap text
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        if len(" ".join(current_line)) > max_width:
            lines.append(" ".join(current_line[:-1]))
            current_line = [word]
    lines.append(" ".join(current_line))
    
    # Draw from bottom up
    y_start = h - 40
    for i, line in enumerate(reversed(lines)):
        (text_w, text_h), _ = cv2.getTextSize(line, font, font_scale, thickness)
        x = (w - text_w) // 2
        y = y_start - (i * (text_h + 15))
        
        # Background
        cv2.rectangle(frame, (x-5, y-text_h-5), (x+text_w+5, y+5), (0,0,0), -1)
        # Text
        cv2.putText(frame, line, (x, y), font, font_scale, (255,255,255), thickness)
        
    return frame

def main():
    parser = argparse.ArgumentParser(description="Real-Time Video Delay Service (Lip-Sync)")
    parser.add_argument("--delay", type=float, default=2.5, help="Retraso en segundos (Default: 2.5)")
    parser.add_argument("--camera", type=str, default="/dev/video0", help="Índice o ruta de la cámara (ej: 0 o /dev/video0)")
    parser.add_argument("--output", type=str, default="/dev/video20", help="Dispositivo de salida (v4l2loopback)")
    parser.add_argument("--width", type=int, default=640, help="Ancho del video")
    parser.add_argument("--height", type=int, default=480, help="Alto del video")
    
    args = parser.parse_args()

    # 1. Configuración inicial
    delay_sec = args.delay
    output_device = args.output
    
    # Manejo de entrada de cámara (puede ser int o str)
    camera_source = args.camera
    if camera_source.isdigit():
        camera_source = int(camera_source)

    check_virtual_camera(output_device)

    # 2. Inicializar OpenCV
    print(f"📷 Abriendo cámara: {camera_source} ...")
    cap = cv2.VideoCapture(camera_source)
    
    # Forzar resolución para consistencia
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    
    # Validar si abrió correctamente
    if not cap.isOpened():
        print(f"❌ Error: No se pudo abrir la cámara {camera_source}")
        sys.exit(1)

    # Obtener specs reales
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0: fps = 30 # Fallback seguro
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"✅ Cámara activa: {width}x{height} @ {fps} FPS")

    # 3. Calcular Buffer
    buffer_size = int(fps * delay_sec)
    frame_buffer = collections.deque(maxlen=buffer_size)
    
    print(f"📦 Buffer configurado: {buffer_size} frames para {delay_sec}s de delay")

    # 4. Inicializar FFmpeg Pipe
    # OpenCV captura en BGR, así que le decimos a FFmpeg que reciba rawvideo bgr24
    ffmpeg_cmd = [
        'ffmpeg',
        '-y', # Sobreescribir
        '-f', 'rawvideo',
        '-vcodec', 'rawvideo',
        '-pix_fmt', 'bgr24',       # Formato nativo de OpenCV
        '-s', f'{width}x{height}', # Tamaño exacto
        '-r', str(fps),            # Tasa de frames
        '-i', '-',                 # Leer de stdin
        '-f', 'v4l2',              # Formato de salida Linux Video
        '-pix_fmt', 'yuv420p',     # Formato compatible con Zoom/Teams
        output_device
    ]

    print(f"🚀 Iniciando Pipeline FFmpeg -> {output_device}")
    
    # Abrimos el subproceso
    try:
        process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("❌ Error: FFmpeg no está instalado.")
        sys.exit(1)
        
    # Manejo de Ctrl+C
    def signal_handler(sig, frame):
        print("\n🛑 Cerrando servicios...")
        cap.release()
        process.stdin.close()
        process.terminate()
        process.wait()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)

    # 5. Loop Principal
    print("⏳ Llenando buffer (Espere... )")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("⚠️ Error leyendo frame de la cámara")
                break
                
            # Añadir al buffer
            frame_buffer.append(frame)
            
            # Lógica de Delay
            if len(frame_buffer) == buffer_size:
                # El buffer está lleno, sacamos el frame más viejo
                delayed_frame = frame_buffer.popleft()
                
                # --- SUBTÍTULOS ---
                try:
                    if os.path.exists("subtitle_stream.txt"):
                        with open("subtitle_stream.txt", "r") as f:
                            current_sub = f.read().strip()
                        delayed_frame = draw_subtitle_multiline(delayed_frame, current_sub)
                except: pass
                
                # Escribir al pipe de FFmpeg
                try:
                    process.stdin.write(delayed_frame.tobytes())
                    process.stdin.flush()
                except BrokenPipeError:
                    print("❌ Error: Pipe de FFmpeg roto (¿se cerró la salida?)")
                    break
            else:
                # Opcional: Feedback visual de carga del buffer
                if len(frame_buffer) % 10 == 0:
                    sys.stdout.write(f"\r⏳ Buffering: {len(frame_buffer)}/{buffer_size} frames")
                    sys.stdout.flush()
                    
    except KeyboardInterrupt:
        pass
    finally:
        signal_handler(None, None)

if __name__ == "__main__":
    main()