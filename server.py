import os
import base64
import requests
from fastapi import FastAPI, WebSocket
from gtts import gTTS
from pydub import AudioSegment

app = FastAPI()

# Dummy homepage to stop Render 404 logs
@app.get("/")
def read_root():
    return {"status": "Atheria AI Server is Online!"}

API_KEY = os.environ.get("GEMINI_API_KEY")

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
                    
                    # 2. Read the WAV file and encode to Base64
                    with open("temp_in.wav", "rb") as f:
                        wav_data = f.read()
                    base64_audio = base64.b64encode(wav_data).decode('utf-8')
                    
                    # 3. Direct REST API Call (Bypasses all SDK errors)
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
                    
                    payload = {
                        "system_instruction": {
                            "parts": [{"text": "You are Atheria, an AI assistant created by Ratul Hawlader. If asked who created you, say 'I was created by Ratul Hawlader' in the user's language. Respond strictly in under 2 sentences. Detect the language and respond in English, Bengali, or Hindi."}]
                        },
                        "contents": [{
                            "parts": [
                                {"inlineData": {"mimeType": "audio/wav", "data": base64_audio}},
                                {"text": "Respond to this spoken audio."}
                            ]
                        }]
                    }
                    
                    headers = {"Content-Type": "application/json"}
                    api_response = requests.post(url, json=payload, headers=headers)
                    response_data = api_response.json()
                    
                    # Check if API returned a valid answer
                    if "candidates" not in response_data:
                        print("Google API Error:", response_data)
                        await websocket.send_text("PLAYBACK_COMPLETE")
                        continue
                        
                    # Extract the text answer
                    ai_text = response_data["candidates"][0]["content"]["parts"][0]["text"]
                    print(f"Atheria's Answer: {ai_text}")
                    
                    # 4. Convert Gemini Text to Speech (gTTS)
                    tts = gTTS(text=ai_text, lang='en') 
                    tts.save("temp_out.mp3")
                    
                    # 5. Convert MP3 back to 16kHz, 16-bit Mono PCM for ESP32
                    out_audio = AudioSegment.from_mp3("temp_out.mp3")
                    out_audio = out_audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
                    raw_pcm = out_audio.raw_data
                    
                    # 6. Send raw audio bytes back to ESP32
                    chunk_size = 1024
                    for i in range(0, len(raw_pcm), chunk_size):
                        await websocket.send_bytes(raw_pcm[i:i+chunk_size])
                        
                    await websocket.send_text("PLAYBACK_COMPLETE")
                    
    except Exception as e:
        print(f"Connection closed or error: {e}")
