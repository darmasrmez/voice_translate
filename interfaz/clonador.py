import os
import torch
import whisper
import sounddevice as sd
import numpy as np
import wavio
import wave
from transformers import pipeline
from TTS.api import TTS
from tkinter import Tk
from tkinter.filedialog import askopenfilename
from scipy.io.wavfile import write as guardarWav



# Parámetros generales
frecuenciaMuestreo = 44100
duracionGrabacion = 10  # segundos
nombreArchivoWav = "miGrabacion.wav"
dispositivo = "cuda" if torch.cuda.is_available() else "cpu"


# Diccionario para XTTS (clonación de voz)
diccionarioIdiomasXTTS = {
    'spanish': 'es',
    'english': 'en',
    'french': 'fr',
    'german': 'de',
    'italian': 'it',
    'russian': 'ru',
    'korean': 'ko',
    'japanese': 'ja',
    'chinese': 'zh-cn',
    'urdu': 'hi'
}

# Diccionario para NLLB (traducción de texto)
diccionarioIdiomasNLLB = {
    'spanish': 'spa_Latn',
    'english': 'eng_Latn',
    'french': 'fra_Latn',
    'german': 'deu_Latn',
    'italian': 'ita_Latn',
    'russian': 'rus_Cyrl',
    'korean': 'kor_Hang',
    'japanese': 'jpn_Jpan',
    'chinese': 'zho_Hans',
    'urdu': 'urd_Arab'
}

# Variable global para almacenar el audio grabado en RAM
audioGrabado = None

# Función de grabar audio
def grabarAudio():
    global audioGrabado
    audioGrabado = sd.rec(
        int(duracionGrabacion * frecuenciaMuestreo),
        samplerate=frecuenciaMuestreo,
        channels=1
    )

# Función para detener y guardar la grabación
def detenerYGuardarGrabacion():
    global audioGrabado
    try:
        sd.stop()
        if audioGrabado is not None:
            # Elimina dimensión innecesaria (Whisper espera 1D)
            audioFinal = np.squeeze(audioGrabado)
            if audioFinal.size == 0:
                print("Audio vacío: no se puede guardar.")
                return None
            wavio.write(nombreArchivoWav, audioFinal, frecuenciaMuestreo, sampwidth=2)
            return os.path.abspath(nombreArchivoWav)
        else:
            print("No se detectó audio grabado.")
            return None
    except Exception as e:
        print("Error al guardar grabación:", e)
        return None

# Verificamos la duración del audio (máx. 10 s)
def verificarDuracionAudio(rutaAudio):
    try:
        with wave.open(rutaAudio, 'rb') as archivo:
            frames = archivo.getnframes()
            rate = archivo.getframerate()
            duracion = frames / float(rate)
            return duracion <= 10
    except Exception as e:
        return False

# Función de cargar audio manual
def cargarAudio():
    ventana = Tk()
    ventana.withdraw()
    rutaArchivo = askopenfilename(
        title="Selecciona un archivo de audio",
        filetypes=[("Archivos WAV", "*.wav")]
    )
    if rutaArchivo:
        if not verificarDuracionAudio(rutaArchivo):
            return "LARGO"
        return rutaArchivo
    else:
        return None

# Transcribimos y detectamos idioma con más control
def transcribirYDetectar(rutaAudio):
    try:
        modeloWhisper = whisper.load_model("base", device=dispositivo)
        audio = whisper.load_audio(rutaAudio)
        audio = whisper.pad_or_trim(audio)
        mel = whisper.log_mel_spectrogram(audio).to(dispositivo)

        _, probabilidades = modeloWhisper.detect_language(mel)
        idiomaDetectado = max(probabilidades, key=probabilidades.get)
        print(f"Idioma detectado: {idiomaDetectado} ({100 * probabilidades[idiomaDetectado]:.2f}%)")

        opciones = whisper.DecodingOptions(task="transcribe", without_timestamps=True)
        resultado = modeloWhisper.decode(mel, opciones)
        texto = resultado.text
        print(f"Texto transcrito:\n{texto}")
        return texto, idiomaDetectado
    except Exception as e:
        print("Error durante la transcripción:", e)
        return "NO SE PUDO TRANSCRIBIR", "desconocido"

# Traducimos con NLLB
def traducirTexto(texto, idiomaOrigen, idiomaDestino):
    traductor = pipeline("translation", model="facebook/nllb-200-distilled-600M")
    try:
        resultado = traductor(texto, src_lang=idiomaOrigen, tgt_lang=idiomaDestino)
        textoTraducido = resultado[0]['translation_text']
        return textoTraducido
    except Exception as e:
        print("Error en traducción:", e)
        return texto

# Clonamos la voz con XTTS
def clonarVoz(texto, rutaAudio, idiomaDestino="spa_Latn"):
    try:
        modelo = TTS(
            model_name="tts_models/multilingual/multi-dataset/xtts_v2",
            progress_bar=False,
            gpu=torch.cuda.is_available()
        )
        modelo.tts_to_file(
            text=texto,
            speaker_wav=rutaAudio,
            language=idiomaDestino,
            file_path="voz_clonada.wav"
        )
    except Exception as e:
        print("Error al clonar voz:", e)

# Sintetizamos voz con Bark

def sintetizarVozBark(texto, idiomaClave, genero, archivoSalida="voz_sintetica.wav"):
    try:
        from bark import generate_audio, SAMPLE_RATE, preload_models
        import scipy.io.wavfile as wavfile
        from torch.serialization import add_safe_globals
        import numpy.core.multiarray

        #Necesario para evitar error de seguridad con PyTorch 2.6+
        add_safe_globals({"numpy.core.multiarray.scalar": numpy.core.multiarray.scalar})

        # Limitar el texto a 250 caracteres (recomendado por Bark)
        if len(texto) > 250:
            texto = texto[:250]

        # Cargar modelos necesarios
        preload_models()

        # Asignar el preset con puros if
        if idiomaClave == "english":
            if genero == "male":
                preset = "v2/en_speaker_9"
            elif genero == "female":
                preset = "v2/en_speaker_6"
            else:
                preset = "v2/en_speaker_9"

        elif idiomaClave == "spanish":
            if genero == "male":
                preset = "v2/es_speaker_6"
            elif genero == "female":
                preset = "v2/es_speaker_3"
            else:
                preset = "v2/es_speaker_6"

        elif idiomaClave == "french":
            preset = "v2/fr_speaker_4"

        elif idiomaClave == "german":
            preset = "v2/de_speaker_3"

        elif idiomaClave == "italian":
            preset = "v2/it_speaker_3"

        elif idiomaClave == "russian":
            preset = "v2/ru_speaker_2"

        elif idiomaClave == "korean":
            preset = "v2/ko_speaker_4"

        elif idiomaClave == "japanese":
            preset = "v2/ja_speaker_3"

        elif idiomaClave == "chinese":
            preset = "v2/zh_speaker_4"

        elif idiomaClave == "urdu":
            preset = "v2/ur_speaker_3"

        else:
            raise ValueError(f"Idioma no soportado: {idiomaClave}")

        # Generar el audio
        audio_array = generate_audio(texto, history_prompt=preset)

        # Guardar el audio
        wavfile.write(archivoSalida, SAMPLE_RATE, audio_array)

    except Exception as e:
        print("Error al sintetizar voz:", repr(e))
