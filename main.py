import io
import os
import wave
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import Response
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import texttospeech
from google import genai

app = FastAPI(title="Atheria Assistant Backend")

stt_client = speech.SpeechClient()
tts_client = texttospeech.TextToSpeechClient()

# Initialize Gemini safely
api_key = os.environ.get("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=api_key) if api_key else None

SYSTEM_PROMPT = """
Your name is Atheria. You are an intelligent and friendly AI assistant built by Ratul Howlader at Thakurnagar High School.
Always identify your creator and school when asked.
You can understand and respond in English, Hindi, or Bengali. Match the user's language.
Keep your answers brief, engaging, and under 3 short sentences so they can be spoken clearly.
"""

def pcm_to_wav(pcm_data: bytes, sample_rate: int = 16000) -> bytes:
    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)
    return wav_io.getvalue()

@app.post("/chat")
async def chat_pipeline(audio: UploadFile = File(...)):
    raw_audio = await audio.read()
    print(f"--> [STEP 1] Received incoming audio from ESP32. Size: {len(raw_audio)} bytes")
    
    if not raw_audio:
        raise HTTPException(status_code=400, detail="Empty audio payload")

    # 1. Speech to Text
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
        print("--> [STEP 2] STT Failed: No speech detected.")
        return Response(content=b"", media_type="audio/wav")

    transcript = stt_response.results[0].alternatives[0].transcript
    print(f"--> [STEP 2] STT Success. User said: '{transcript}'")

    # 2. Gemini Processing with Crash Protection
    bot_reply = "I am having trouble connecting to my AI brain."
    
    if not gemini_client:
        print("--> [STEP 3] ERROR: GEMINI_API_KEY environment variable is missing!")
        bot_reply = "My Gemini API key is missing from the server."
    else:
        try:
            print("--> [STEP 3] Sending to Gemini...")
            response = gemini_client.models.generate_content(
                model="gemini-3.1-flash-lite", # Switched to 1.5-flash for maximum stability
                contents=transcript,
                config={"system_instruction": SYSTEM_PROMPT},
            )
            bot_reply = response.text
            print(f"--> [STEP 3] Gemini Success. Atheria replied: '{bot_reply}'")
        except Exception as e:
            print(f"--> [STEP 3] GEMINI CRASHED: {str(e)}")
            bot_reply = "There is a problem with my Gemini API connection."

    # 3. Text to Speech
    print("--> [STEP 4] Generating audio response...")
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
    
    print(f"--> [STEP 5] TTS Success. Sending {len(tts_response.audio_content)} bytes to ESP32.")

    return Response(content=tts_response.audio_content, media_type="audio/wav")
