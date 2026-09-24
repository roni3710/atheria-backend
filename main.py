import io
import os
import wave
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import texttospeech
from google import genai

app = FastAPI(title="Atheria Assistant Backend")

# Initialize Google Cloud clients
stt_client = speech.SpeechClient()
tts_client = texttospeech.TextToSpeechClient()
gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Persona system instructions
SYSTEM_PROMPT = """
Your name is Atheria. You are an intelligent and friendly AI assistant built by an electrical engineering student at Brainware University.
Always identify your creator and school when asked.
You can understand and respond in English, Hindi, or Bengali. Match the user's language.
Keep your answers brief, engaging, and under 3 short sentences so they can be spoken clearly.
"""

def pcm_to_wav(pcm_data: bytes, sample_rate: int = 16000) -> bytes:
    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)
    return wav_io.getvalue()

@app.post("/chat")
async def chat_pipeline(audio: UploadFile = File(...)):
    raw_audio = await audio.read()
    if not raw_audio:
        raise HTTPException(status_code=400, detail="Empty audio payload")

    # 1. Speech to Text (Supports English, Hindi, Bengali)
    audio_wav = pcm_to_wav(raw_audio, sample_rate=16000)
    audio_obj = speech.RecognitionAudio(content=audio_wav)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-IN",
        alternative_language_codes=["hi-IN", "bn-IN"],
        enable_automatic_punctuation=True,
    )

    stt_response = stt_client.recognize(config=config, audio=audio_obj)
    if not stt_response.results:
        return Response(content=b"", media_type="audio/wav")

    transcript = stt_response.results[0].alternatives[0].transcript
    print(f"Recognized: {transcript}")

    # 2. Gemini Model Processing
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=transcript,
        config={"system_instruction": SYSTEM_PROMPT},
    )
    bot_reply = response.text
    print(f"Atheria: {bot_reply}")

    # 3. Text to Speech
    synthesis_input = texttospeech.SynthesisInput(text=bot_reply)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-IN",
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
    )

    tts_response = tts_client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    return Response(content=tts_response.audio_content, media_type="audio/wav")
