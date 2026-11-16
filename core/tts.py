import io
import re
import base64
from core.config import KOKORO_ONNX_PATH, KOKORO_VOICES_PATH, TTS_CPU_THREADS
from core.utils import is_text_spanish

def load_tts_model():
    """Carga el modelo Kokoro-82M ONNX con sesión multihilo optimizada (4x más rápido en CPU)."""
    import onnxruntime as ort
    from kokoro_onnx import Kokoro

    print("[TTS] Inicializando Kokoro TTS ONNX (6 hilos)...")
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = TTS_CPU_THREADS
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    sess = ort.InferenceSession(KOKORO_ONNX_PATH, sess_options=opts, providers=["CPUExecutionProvider"])
    model = Kokoro.from_session(sess, KOKORO_VOICES_PATH)
    print("✓ Kokoro listo con sesión multihilo de alto rendimiento (~450 ms)")
    return model

def clean_tts_text(text: str) -> str:
    """
    Sanitiza el texto previo a la síntesis.
    Elimina asteriscos de rol (*sonríe*, *laughs*), paréntesis narrativos y emojis.
    Preserva signos de interrogación/admiración y acentos en español.
    """
    if not text:
        return ""
    # 1. Eliminar acciones narrativas entre asteriscos o paréntesis
    t = re.sub(r'\*.*?\*', '', text)
    t = re.sub(r'\(.*?\)', '', t)
    # 2. Eliminar emojis y caracteres no fonéticos
    t = re.sub(r'[^\w\s.,!?:;¿¡áéíóúÁÉÍÓÚñÑüÜ\'\"-]', '', t)
    # 3. Normalizar espacios
    return re.sub(r'\s+', ' ', t).strip()

VOICE_BLENDS = {
    "blend_dora_sarah": [("ef_dora", 0.60), ("af_sarah", 0.40)],
    "blend_alex_adam": [("em_alex", 0.60), ("am_adam", 0.40)],
}
_CACHED_BLENDS = {}

def get_voice_target(tts_model, voice_name: str):
    """Retorna el nombre de la voz o el tensor de estilo interpolado/clonado en memoria."""
    if voice_name in VOICE_BLENDS:
        if voice_name not in _CACHED_BLENDS and tts_model:
            try:
                blend_spec = VOICE_BLENDS[voice_name]
                combined = None
                for v_name, weight in blend_spec:
                    style = tts_model.get_voice_style(v_name)
                    if combined is None:
                        combined = weight * style
                    else:
                        combined = combined + (weight * style)
                _CACHED_BLENDS[voice_name] = combined
            except Exception as e:
                print(f"Error generando mezcla de voz {voice_name}: {e}")
                return blend_spec[0][0]
        return _CACHED_BLENDS.get(voice_name, voice_name)
    return voice_name

def synthesize_audio_wav_base64(
    tts_model,
    text: str,
    voice_name: str = "ef_dora",
    lang: str = "auto",
    whisper_mode: bool = False
) -> str:
    """
    Sintetiza texto a audio WAV codificado en Base64.
    Aplica fonemizador nativo G2P ("es" para español, "en-us" para inglés),
    soporte para voces compuestas/híbridas y modulación para Modo Susurro.
    """
    import soundfile as sf
    text_clean = clean_tts_text(text)
    if not text_clean or not tts_model:
        return ""

    actual_lang = "es"
    try:
        # Determinar idioma exacto para el fonemizador G2P nativo de Kokoro
        if lang == "auto":
            is_es = voice_name.startswith("e") or is_text_spanish(text_clean)
            actual_lang = "es" if is_es else "en-us"
        else:
            actual_lang = "es" if lang == "es" else "en-us"

        # Cadencia natural
        speed = 1.08 if actual_lang == "es" else 1.12
        clause_pause = 0.1
        sentence_pause = 0.2

        # Ajuste para Modo Susurro / Noche: ritmo relajado y pausas sutiles
        if whisper_mode:
            speed = speed * 0.90
            clause_pause = 0.15
            sentence_pause = 0.25

        target_voice = get_voice_target(tts_model, voice_name)

        samples, sr = tts_model.create(
            text_clean,
            voice=target_voice,
            speed=speed,
            lang=actual_lang,
            sentence_pause=sentence_pause,
            clause_pause=clause_pause
        )

        # Atenuación de amplitud para Modo Susurro
        if whisper_mode:
            samples = samples * 0.52

        buf = io.BytesIO()
        sf.write(buf, samples, sr, format='WAV')
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('utf-8')
    except Exception as e:
        print(f"Error en síntesis TTS ({voice_name}, lang={actual_lang}): {e}")
        return ""
