import os
import io
from fastapi import FastAPI, Request, Response
import google.generativeai as genai
from gtts import gTTS
from pydub import AudioSegment

app = FastAPI()

SYSTEM_INSTRUCTION = """
Your name is Atheria. You are an AI voice assistant.
You are friendly, helpful, and concise.
You can converse fluently in Bengali, Hindi, and English.
Keep responses short (1-2 sentences maximum).
"""

@app.get("/")
def health_check():
    return {"status": "Atheria backend is live!"}

@app.post("/process-voice")
async def process_voice(request: Request):
    try:
        # Load API key dynamically per request
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            print("Error: GEMINI_API_KEY environment variable is missing.")
            return Response(content=b"API Key Missing", status_code=500)

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=SYSTEM_INSTRUCTION
        )

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
Step 2: Update Dockerfile
Update your Dockerfile to use exec uvicorn so that Cloud Run's injected $PORT variable is bound correctly:
FROM python:3.11-slim

# Install system dependencies (ffmpeg required by pydub)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt-get/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

# Use exec format so $PORT evaluates cleanly
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
