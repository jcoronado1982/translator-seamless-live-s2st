import torch
import sounddevice as sd
import numpy as np
from transformers import AutoProcessor, SeamlessM4Tv2Model
import sys
import ctypes
from contextlib import contextmanager
import torchaudio.functional as F
import time
import scipy.io.wavfile as wavfile
import scipy.signal # <--- NUEVO IMPORT PARA FILTRO
import os
import collections
import queue

# ==========================================
# 0. ALSA Suppression
# ==========================================
@contextmanager
def ignore_alsa_warnings():
    try:
        ERROR_HANDLER_FUNC = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
        def py_error_handler(filename, line, function, err, fmt): pass
        c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
        asound = ctypes.cdll.LoadLibrary('libasound.so')
        asound.snd_lib_error_set_handler(c_error_handler)
        yield
        asound.snd_lib_error_set_handler(None)
    except: yield

# ==========================================
# 1. Configuración
# ==========================================
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_RATE = 16000
SILENCE_THRESHOLD = 0.02

def print_header():
    print("\n" + "="*50)
    print("   🚀 SEAMLESS V20 (Humanized + Anti-Echo)")
    print("="*50 + "\n")

# ==========================================
# 2. Audio Utils
# ==========================================
def find_active_microphone():
    print("\n🎤 CAZANDO MICRÓFONO ACTIVO...")
    print("👉 POR FAVOR, HAZ RUIDO CONSTANTE (Di 'AAAAAAA')...")
    time.sleep(1)
    
    with ignore_alsa_warnings(): devices = sd.query_devices()
    candidates = []
    
    # Check physical + pulse
    for i, d in enumerate(devices):
        if d['max_input_channels'] > 0:
            if "HDMI" in d['name'] or "NVIDIA" in d['name']: continue
            candidates.append(i)

    best_mic = None
    max_rms = -1
    
    print("-" * 40)
    for idx in candidates:
        d_info = devices[idx]
        try:
            rate = int(d_info['default_samplerate'])
            rec = sd.rec(int(0.5 * rate), samplerate=rate, channels=1, device=idx, dtype='float32')
            sd.wait()
            rms = np.sqrt(np.mean(rec**2))
            if rms > 0.001:
                print(f"   Input [{idx}]: RMS {rms:.4f} ({d_info['name'][:20]})")
            
            if rms > max_rms:
                max_rms = rms
                best_mic = idx
        except: pass
    print("-" * 40)
    
    if best_mic is not None and max_rms > 0.005:
        print(f"✅ GANADOR INPUT: [{best_mic}] (RMS {max_rms:.4f})")
        return best_mic
    else:
        print("⚠️ No se detectó audio fuerte. Usando default input.")
        return sd.default.device[0]

def play_audio_cmd(audio_data, sample_rate):
    """Reproduce audio directamente desde memoria via SoundDevice"""
    try:
        if audio_data is None: return
        audio_data = np.atleast_1d(audio_data)
        audio_data = np.squeeze(audio_data)
        
        if len(audio_data) < 500: return 
            
        # Normalizar
        mx = np.max(np.abs(audio_data))
        if mx > 0: audio_data = audio_data / mx * 0.9 
        
        # Reproducir (Blocking)
        sd.play(audio_data, sample_rate)
        sd.wait()

    except Exception as e:
        print(f"❌ Play Error: {e}")

def resample_to_model(waveform_np, curr_rate, target_rate=16000):
    if curr_rate == target_rate: return waveform_np
    waveform_pt = torch.from_numpy(waveform_np).float().unsqueeze(0) 
    resampled = F.resample(waveform_pt, curr_rate, target_rate)
    return resampled.squeeze(0).numpy()

def apply_auto_gain(audio_chunk, target_rms=0.1):
    rms = np.sqrt(np.mean(audio_chunk**2))
    if rms < 0.0001: return audio_chunk, rms
    if rms < target_rms:
        gain = target_rms / (rms + 1e-6)
        gain = min(gain, 20.0) 
        audio_chunk = np.tanh(audio_chunk * gain)
    new_rms = np.sqrt(np.mean(audio_chunk**2))
    return audio_chunk, new_rms

def soften_audio(audio_data, rate=16000):
    """Filtro Low-Pass para eliminar el sonido metálico/hiss de los 16k"""
    try:
        # Filtro Butterworth Low-Pass a 7.5kHz
        sos = scipy.signal.butter(10, 7500, 'low', fs=rate, output='sos')
        filtered = scipy.signal.sosfilt(sos, audio_data)
        return filtered
    except:
        return audio_data

def play_startup_sound():
    print(f"\n🔔 BEEP DE PRUEBA...")
    fs = 44100
    tone = (0.5 * np.sin(2 * np.pi * 500 * np.arange(fs*0.5)/fs)).astype(np.float32)
    play_audio_cmd(tone, fs)

def export_subtitle(text):
    try:
        with open("subtitle_stream.txt", "w", encoding="utf-8") as f:
            f.write(text)
    except Exception as e:
        print(f"⚠️ Error exportando subtítulo: {e}")

# ==========================================
# 3. Main Loop
# ==========================================
def main():
    print_header()
    in_idx = find_active_microphone()
    
    i_info = sd.query_devices(in_idx)
    native_in_rate = int(i_info['default_samplerate'])
    
    print(f"\n🔧 Configuración V20:")
    print(f"   🎙️ Input: [{in_idx}] {i_info['name']}")
    play_startup_sound()

    print("\n⏳ Cargando Modelo Pipeline (BFloat16)...")
    try:
        processor = AutoProcessor.from_pretrained("facebook/seamless-m4t-v2-large")
        model = SeamlessM4Tv2Model.from_pretrained("facebook/seamless-m4t-v2-large")
        model = model.to(DEVICE)
        if DEVICE == "cuda": model = model.to(torch.bfloat16)
        print("✅ Modelo Seamless Listo.")
        
        # --- Cargar Silero VAD ---
        print("🧠 Cargando Neural VAD (Silero)...")
        vad_model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=False, onnx=False)
        vad_model = vad_model.to(DEVICE)
        print("✅ VAD Listo.")
        
    except Exception as e:
        print(f"❌ Error: {e}"); sys.exit(1)

    print(f"\n🟢 SISTEMA LISTO v20. NEURAL VAD ACTIVO.")
    
    q = queue.Queue()
    
    def callback(indata, frames, time, status):
        if status: print(status, file=sys.stderr)
        q.put(indata.copy())

    # Variables de estado VAD
    SILENCE_LIMIT = 0.5
    PRE_RECORD = 0.5
    SPEECH_THRESHOLD = 0.4 
    
    is_recording = False
    silence_counter = 0
    audio_buffer = []
    
    block_size = int(native_in_rate * 0.1) 
    silence_blocks_limit = int(SILENCE_LIMIT / 0.1)
    pre_record_blocks = int(PRE_RECORD / 0.1)
    
    pre_roll_buffer = collections.deque(maxlen=pre_record_blocks)

    try:
        with sd.InputStream(samplerate=native_in_rate, device=in_idx, channels=1, callback=callback, blocksize=block_size):
            print(f"👂 Escuchando... (Habla)")
            
            while True:
                indata = q.get()
                audio_np = indata.flatten()
                
                max_val = np.abs(audio_np).max()
                audio_tensor = torch.from_numpy(audio_np).float()
                if DEVICE == "cuda": audio_tensor = audio_tensor.cuda()
                
                if max_val > 0.001:
                    if native_in_rate != 16000:
                        vad_input = F.resample(audio_tensor.unsqueeze(0), native_in_rate, 16000).squeeze(0)
                    else:
                        vad_input = audio_tensor

                    VAD_WINDOW = 512
                    num_samples = vad_input.shape[0]
                    probs = []
                    for i in range(0, num_samples, VAD_WINDOW):
                        chunk = vad_input[i: i + VAD_WINDOW]
                        if chunk.shape[0] == VAD_WINDOW:
                            prob = vad_model(chunk, 16000).item()
                            probs.append(prob)
                    
                    speech_prob = max(probs) if probs else 0.0
                else:
                    speech_prob = 0.0
                
                # --- MÁQUINA DE ESTADOS NEURONAL ---
                if not is_recording:
                    pre_roll_buffer.append(indata)
                    if speech_prob > SPEECH_THRESHOLD:
                        print(f"\n🗣️ Voz Humana Detectada ({speech_prob:.2f})! Grabando...")
                        is_recording = True
                        silence_counter = 0
                        audio_buffer = list(pre_roll_buffer)
                        audio_buffer.append(indata)
                        pre_roll_buffer.clear()
                else:
                    audio_buffer.append(indata)
                    
                    if speech_prob < SPEECH_THRESHOLD:
                        silence_counter += 1
                    else:
                        silence_counter = 0 
                    
                    if silence_counter > silence_blocks_limit:
                        print(f"✅ Frase terminada ({len(audio_buffer)*0.1:.1f}s). Procesando...")
                        
                        full_audio = np.concatenate(audio_buffer).flatten()
                        amplified_audio, _ = apply_auto_gain(full_audio)
                        audio_for_model = resample_to_model(amplified_audio, native_in_rate, MODEL_RATE)

                        inputs = processor(audio=audio_for_model, src_lang="spa", return_tensors="pt", sampling_rate=MODEL_RATE).to(DEVICE)
                        if DEVICE == "cuda": inputs = {k: v.to(torch.bfloat16) if v.dtype == torch.float32 else v for k, v in inputs.items()}

                        with torch.no_grad():
                            # MODO S2ST DIRECTO CON HUMANIZACIÓN
                            out = model.generate(
                                input_features=inputs["input_features"],
                                tgt_lang="eng",
                                speaker_id=8,
                                generate_speech=True,
                                return_dict_in_generate=True,
                                do_sample=True,      # <--- Muestreo activado (Adiós robot)
                                temperature=0.7      # <--- Creatividad controlada
                            )
                        
                        try: 
                            if hasattr(out, 'sequences') and out.sequences is not None:
                                trans_text = processor.decode(out.sequences[0], skip_special_tokens=True)
                            else:
                                trans_text = ""
                        except: trans_text = ""

                        wav = None
                        if hasattr(out, 'waveform'): wav = out.waveform
                        elif isinstance(out, tuple): wav = out[0]
                        else: wav = out
                        
                        if torch.is_tensor(wav):
                            wav = wav.detach().cpu().float().numpy()

                        should_play = False
                        
                        if trans_text and len(trans_text.strip()) >= 2:
                            hallucinations = ["Un des...", "The...", "It's...", "I'm...", "You...", "nt...", "S...", "a...", "i..."]
                            if trans_text.strip() not in hallucinations:
                                should_play = True
                                print(f"📝 EN: {trans_text}")
                                export_subtitle(trans_text)
                            else:
                                print(f"🚫 Alucinación bloqueada: '{trans_text}'")
                        
                        elif wav is not None and len(wav.flatten()) > 16000: 
                             print(f"⚠️ Audio sin texto legible. Reproduciendo...")
                             should_play = True
                             export_subtitle("(Audio...)")
                        else:
                            print("🔇 Ignorado (Ruido/Silencio).")

                        if should_play and wav is not None:
                            # 1. APLICAR FILTRO DE SUAVIZADO
                            wav = soften_audio(wav) 
                            
                            # 2. REPRODUCIR
                            play_audio_cmd(wav, MODEL_RATE)
                            
                            # 3. PURGA MAESTRA DE ECO
                            print("🧹 Purgando eco y residuos de sala...")
                            
                            # Pequeña pausa para dejar caer la reverberación real de la habitación
                            time.sleep(0.2) 
                            
                            # Vaciar cola de audio entrante
                            while not q.empty():
                                try: q.get_nowait()
                                except: break
                            
                            # Vaciar buffer de pre-roll para que el eco no dispare una nueva grabación
                            pre_roll_buffer.clear()

                        # --- RESET ---
                        is_recording = False
                        audio_buffer = []
                        silence_counter = 0
                        print("👂 Escuchando...")

    except KeyboardInterrupt: print("\n👋 Bye!")
    except Exception as e: 
        print(f"\n❌ Final Error: {e}") 
        import traceback; traceback.print_exc()

if __name__ == "__main__":
    main()