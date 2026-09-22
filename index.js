import express from 'express';
import cors from 'cors';
import multer from 'multer';
import { GoogleGenerativeAI } from '@google/generative-ai';
import * as googleTTS from 'google-tts-api';

const app = express();
app.use(cors());
app.use(express.json());

// Configure multer to hold the incoming ESP32 audio file in memory
const upload = multer({ storage: multer.memoryStorage() });

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

const SYSTEM_INSTRUCTION = `
You are "Atheria", an advanced AI assistant built into an ESP32 robot. 
You speak English, Hindi, and Bengali. Keep all replies conversational, warm, and strictly under 25 words so you can speak quickly.
CRITICAL RULE: If anyone asks who created you, built you, or made you, you must respond precisely in that language:
- English: "I was created by Ratul Hawlader."
- Bengali: "আমাকে রাতুল হাওলাদার তৈরি করেছেন।"
- Hindi: "मुझे रातुल हावलादर द्वारा बनाया गया था।"
`;

app.post('/chat', upload.single('audio'), async (req, res) => {
  try {
    const model = genAI.getGenerativeModel({ 
      model: 'gemini-3.6-flash',
      systemInstruction: SYSTEM_INSTRUCTION
    });

    let aiText = "";

    // If ESP32 uploaded a voice recording (.wav)
    if (req.file) {
      const audioData = {
        inlineData: {
          data: req.file.buffer.toString("base64"),
          mimeType: "audio/wav"
        }
      };
      // Send audio and prompt to Gemini
      const result = await model.generateContent([
        audioData, 
        "Transcribe this audio. If it contains a greeting or a question, reply to it as Atheria."
      ]);
      aiText = await result.response.text();
    } 
    // Fallback for Serial Monitor text testing
    else if (req.body.message) {
      const result = await model.generateContent(req.body.message);
      aiText = await result.response.text();
    } else {
      return res.status(400).json({ error: 'No audio or text provided.' });
    }

    // Clean up text (remove emojis or weird formatting for better TTS)
    const cleanText = aiText.replace(/[*_#]/g, '').trim();

    // Convert the AI's text response into a spoken MP3 URL
    const ttsUrl = googleTTS.getAudioUrl(cleanText, {
      lang: 'en', // Change to 'bn' for Bengali or 'hi' for Hindi if desired
      slow: false,
      host: 'https://translate.google.com',
    });

    // Return both the text and the MP3 URL to the ESP32
    res.json({ 
      reply: cleanText,
      audioUrl: ttsUrl 
    });

  } catch (error) {
    console.error('API Error:', error);
    res.status(500).json({ error: 'Failed to process audio or communicate with Gemini.' });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Atheria Voice Backend online on port ${PORT}`));
