import os
import io
from fastapi import FastAPI, WebSocket
import google.generativeai as genai
from gtts import gTTS
from pydub import AudioSegment

app = FastAPI()

# Configure Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction="You are Atheria, an AI assistant created by Ratul Hawlader. "
                       "If asked who created you, say 'I was created by Ratul Hawlader' in the user's language. "
                       "Respond strictly in under 2 sentences. Detect the language and respond in English, Bengali, or Hindi."
)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    audio_buffer = bytearray()
    
    try:
        while True:
            message = await websocket.receive()
            
            if "bytes" in message:
                # Accumulate raw audio bytes from ESP32
                audio_buffer.extend(message["bytes"])
                
            elif "text" in message:
                command = message["text"]
                if command == "PROCESS_AUDIO" and len(audio_buffer) > 0:
                    # 1. Save received raw PCM to a WAV file
                    audio_segment = AudioSegment(
                        data=bytes(audio_buffer),
                        sample_width=2, # 16-bit
                        frame_rate=16000,
                        channels=1
                    )
                    audio_segment.export("temp_in.wav", format="wav")
                    audio_buffer.clear() # Reset for next recording
                    
                    # 2. Send to Gemini
                    audio_file = genai.upload_file(path="temp_in.wav")
                    response = model.generate_content([audio_file, "Respond to this audio."])
                    
                    # 3. Convert Gemini Text to Speech (gTTS)
                    tts = gTTS(text=response.text, lang='en') # Note: You can parse Gemini's output to set lang dynamically
                    tts.save("temp_out.mp3")
                    
                    # 4. Convert MP3 back to 16kHz, 16-bit Mono PCM for ESP32
                    out_audio = AudioSegment.from_mp3("temp_out.mp3")
                    out_audio = out_audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
                    raw_pcm = out_audio.raw_data
                    
                    # 5. Send raw audio bytes back to ESP32
                    chunk_size = 1024
                    for i in range(0, len(raw_pcm), chunk_size):
                        await websocket.send_bytes(raw_pcm[i:i+chunk_size])
                        
                    await websocket.send_text("PLAYBACK_COMPLETE")
                    
    except Exception as e:
        print(f"Connection closed or error: {e}")
