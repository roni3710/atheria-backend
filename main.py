import os
import io
import static_ffmpeg
from fastapi import FastAPI, Request, Response
import google.generativeai as genai
from gtts import gTTS
from pydub import AudioSegment

# Initialize static ffmpeg binaries
static_ffmpeg.add_paths()

app = FastAPI()

# Safely configure Gemini API key
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = """
Your name is Atheria. You are an AI voice assistant.
You are friendly, helpful, and concise.
You can converse fluently in Bengali, Hindi, and English.
Keep responses short (1-2 sentences maximum).
"""

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

@app.get("/")
def health_check():
    return {"status": "Atheria backend is live!"}

@app.post("/process-voice")
async def process_voice(request: Request):
    try:
        audio_bytes = await request.body()

        if len(audio_bytes) < 1000:
            user_prompt = "Hello! Please introduce yourself briefly."
            response = model.generate_content(user_prompt)
        else:
            audio_part = {
                "mime_type": "audio/wav",
                "data": audio_bytes
            }
            response = model.generate_content([audio_part, "Listen to this audio and reply concisely as Atheria."])

        bot_reply = response.text if response.text else "Hello, I am Atheria!"
        print(f"Atheria reply: {bot_reply}")

        # Convert text reply to Speech
        tts = gTTS(text=bot_reply, lang='en', slow=False)
        
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)

        # Convert MP3 to 16kHz mono PCM for ESP32
        audio_segment = AudioSegment.from_file(mp3_fp, format="mp3")
        audio_segment = audio_segment.set_frame_rate(16000).set_channels(1).set_sample_width(2)

        return Response(content=audio_segment.raw_data, media_type="application/octet-stream")

    except Exception as e:
        print(f"Error in backend: {e}")
        return Response(content=b"", status_code=500)
