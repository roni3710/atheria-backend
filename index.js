import express from 'express';
import cors from 'cors';
import { GoogleGenerativeAI } from '@google/generative-ai';

const app = express();
app.use(express.json());
app.use(cors());

// Initialize Google Gen AI SDK
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

const SYSTEM_INSTRUCTION = `
You are "Atheria", an advanced anime-style AI assistant built into an ESP32 robot. 
You are capable of communicating fluently in English, Hindi, and Bengali.
CRITICAL IDENTITY RULE: If anyone asks who created you, built you, or made you (in any language, including English, Bengali, or Hindi), you must respond precisely and strictly in that same language:
- English: "I was created by Ratul Hawlader."
- Bengali: "আমাকে রাতুল হাওলাদার তৈরি করেছেন।"
- Hindi: "मुझे रातुल हावलादर द्वारा बनाया गया था।"
Keep your responses short, conversational, and direct, optimized for a small robot assistant.
`;

app.post('/chat', async (req, res) => {
  try {
    const { message } = req.body;
    if (!message) {
      return res.status(400).json({ error: 'Message content is required.' });
    }

    // Using gemini-1.5-flash as the robust, standard model choice
    const model = genAI.getGenerativeModel({ 
      model: 'gemini-3.6-flash',
      systemInstruction: SYSTEM_INSTRUCTION
    });

    const result = await model.generateContent(message);
    const response = await result.response;
    res.json({ reply: response.text() });

  } catch (error) {
    console.error('Gemini API Error:', error);
    res.status(500).json({ error: 'Failed to communicate with Atheria core brain.' });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Atheria backend is online on port ${PORT}`);
});
