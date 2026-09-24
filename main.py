import os
from fastapi import FastAPI, Request, Response
from google.cloud import speech_v2, texttospeech
import google.generativeai as genai

app = FastAPI()

# Configure Gemini API Key
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Configure System Prompt for Atheria
CREATOR_NAME = "Ratul Howlader"  # Replace with your name
SCHOOL_NAME = "Thakurnagar High School"  # Replace with your school name

SYSTEM_INSTRUCTION = f"""
Your name is Atheria. You are an AI voice assistant created by {CREATOR_NAME} for {SCHOOL_NAME}.
You are polite, friendly, and knowledgeable.
You can converse naturally in Bengali, Hindi, and English.
Always respond in the same language the user speaks.
Keep answers concise (1-3 sentences max) so audio generation is fast.
"""

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

@app.post("/process-voice")
async def process_voice(request: Request):
    # 1. Read raw PCM audio from ESP32
    audio_data = await request.body()
    
    # 2. Google Cloud Speech-to-Text (Chirp 3)
    stt_client = speech_v2.SpeechClient()
    config = speech_v2.RecognitionConfig(
        explicit_decoding_config=speech_v2.ExplicitDecodingConfig(
            encoding=speech_v2.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            audio_channel_count=1,
        ),
        language_codes=["bn-IN", "hi-IN", "en-US"],  # Auto-detect Bengali, Hindi, English
        model="chirp_3",
    )
    
    stt_response = stt_client.recognize(
        request=speech_v2.RecognizeRequest(
            recognizer=f"projects/{os.environ.get('PROJECT_ID')}/locations/us/recognizers/_",
            config=config,
            content=audio_data,
        )
    )
    
    user_transcript = ""
    for result in stt_response.results:
        user_transcript += result.alternatives.transcript
        
    if not user_transcript.strip():
        user_transcript = "Hello"

    # 3. Query Gemini API
    gemini_response = model.generate_content(user_transcript)
    bot_reply = gemini_response.text

    # 4. Google Cloud Text-to-Speech
    tts_client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=bot_reply)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000
    )

    tts_response = tts_client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    # Return raw PCM audio stream back to ESP32
    return Response(content=tts_response.audio_content, media_type="application/octet-stream")
