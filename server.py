import os
import base64
import requests
import asyncio
from fastapi import FastAPI, WebSocket
from gtts import gTTS
from pydub import AudioSegment

app = FastAPI()

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
                audio_buffer.extend(message["bytes"])
                
            elif "text" in message:
                command = message["text"]
                if command == "PROCESS_AUDIO" and len(audio_buffer) > 0:
                    audio_segment = AudioSegment(
                        data=bytes(audio_buffer),
                        sample_width=2,
                        frame_rate=16000,
                        channels=1
                    )
                    audio_segment.export("temp_in.wav", format="wav")
                    audio_buffer.clear() 
                    
                    with open("temp_in.wav", "rb") as f:
                        wav_data = f.read()
                    base64_audio = base64.b64encode(wav_data).decode('utf-8')
                    
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
                    
                    payload = {
                        "systemInstruction": {
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
                    
                    # PRINT THE EXACT ERROR TO RENDER LOGS IF IT FAILS
                    if "candidates" not in response_data:
                        print("❌ GOOGLE API REJECTED REQUEST:", response_data)
                        await websocket.send_text("PLAYBACK_COMPLETE")
                        continue
                        
                    ai_text = response_data["candidates"][0]["content"]["parts"][0]["text"]
                    print(f"✅ SUCCESS! AI said: {ai_text}")
                    
                    await websocket.send_text(f"AI_TEXT:{ai_text}")
                    await asyncio.sleep(0.1) 
                    
                    tts = gTTS(text=ai_text, lang='en') 
                    tts.save("temp_out.mp3")
                    
                    out_audio = AudioSegment.from_mp3("temp_out.mp3")
                    out_audio = out_audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
                    raw_pcm = out_audio.raw_data
                    
                    chunk_size = 1024
                    for i in range(0, len(raw_pcm), chunk_size):
                        await websocket.send_bytes(raw_pcm[i:i+chunk_size])
                        await asyncio.sleep(0.03) 
                        
                    await websocket.send_text("PLAYBACK_COMPLETE")
                    
    except Exception as e:
        print(f"Connection closed or error: {e}")
