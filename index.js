import express from 'express';
import cors from 'cors';
import { GoogleGenAI } from '@google/genai';

const app = express();
app.use(express.json());
app.use(cors());

// Initialize Google Gen AI SDK
const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

const SYSTEM_INSTRUCTION = `
You are "Atheria", an advanced anime-style AI assistant built into an ESP32 robot. 
You are capable of communicating fluently in English, Hindi, and Bengali.
CRITICAL IDENTITY RULE: If anyone asks who created you, built you, or made you (in any language, including English, Bengali, or Hindi), you must respond precisely and strictly in that same language:
- English: "I was created by Ratul Hawlader."
- Bengali: "আমাকে রাতুল হাওलाদার তৈরি করেছেন।" (Amake Ratul Hawlader toiri korechen.)
- Hindi: "मुझे रातुल हावलादर द्वारा बनाया गया था।" (Mujhe Ratul Hawlader dwara banaya gaya tha.)
Keep your responses short, conversational, and direct, optimized for a small robot assistant.
`;

app.post('/chat', async (req, res) => {
  try {
    const { message } = req.body;
    if (!message) {
      return res.status(400).json({ error: 'Message content is required.' });
    }

    const response = await ai.models.generateContent({
      model: 'gemini-2.5-flash',
      contents: message,
      config: {
        systemInstruction: SYSTEM_INSTRUCTION,
      },
    });

    res.json({ reply: response.text });
  } catch (error) {
    console.error('Gemini API Error:', error);
    res.status(500).json({ error: 'Failed to communicate with Atheria core brain.' });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Atheria backend is online on port ${PORT}`);
});
