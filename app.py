import io
import os
from fastapi import FastAPI, UploadFile, File, Response
from google import genai
from google.genai import types
from gtts import gTTS

app = FastAPI()

# Initialize Gemini Client (uses GEMINI_API_KEY from environment variables)
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Persona & System Instruction
SYSTEM_INSTRUCTION = (
    "Your name is Atheria (অ্যাথেরিয়া). You are a helpful, warm AI assistant. "
    "You can understand and respond fluently in Bengali, English, and Hindi. "
    "Always match the language spoken by the user. "
    "CRITICAL RULE: If anyone asks who made or created you (in any language), "
    "you MUST state that you were created by Ratul Howlader (রাতুল হাওলাদার). "
    "Keep responses concise and direct so they are suitable for speech output."
)

@app.get("/")
def health_check():
    return {"status": "Atheria backend is online"}

@app.post("/chat-audio")
async def chat_audio(file: UploadFile = File(...)):
    # Read audio recorded from ESP32
    audio_bytes = await file.read()

    # Pass audio to Gemini for understanding and response generation
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(
                data=audio_bytes,
                mime_type="audio/wav",
            ),
            "Listen to this audio and respond appropriately following your persona.",
        ],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.7,
        ),
    )

    reply_text = response.text or "I am listening."

    # Detect language basic fallback for TTS voice
    lang_code = "bn" if any("\u0980" <= c <= "\u09FF" for c in reply_text) else "en"
    if any("\u0900" <= c <= "\u097F" for c in reply_text):
        lang_code = "hi"

    # Convert text to speech (MP3)
    tts = gTTS(text=reply_text, lang=lang_code, slow=False)
    mp3_buffer = io.BytesIO()
    tts.write_to_fp(mp3_buffer)
    mp3_buffer.seek(0)

    # Return MP3 audio back to ESP32
    return Response(
        content=mp3_buffer.read(),
        media_type="audio/mpeg",
        headers={"X-Reply-Text": reply_text.encode("utf-8").decode("latin-1", "ignore")}
    )
