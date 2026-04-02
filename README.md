🛡️ FinGuard AI – Financial Misinformation Detection

FinGuard AI is an AI-powered assistant that detects financial misinformation and scams in real-time.
It helps users verify WhatsApp messages related to investments, IPOs, cryptocurrencies, and stock market rumors by classifying them as Scam 🚨, Warning ⚠️, or Legit ✅.

This project was built as part of a Google GenAI Hackathon.

🚀 Features

✅ WhatsApp integration using Twilio API
🤖 AI-based classification with Google Vertex AI (Gemini 2.0 Flash)
🔍 Cross-checks with trusted sources (SEBI, RBI, BSE updates)
📊 Data storage and analytics with Firestore + BigQuery
⚡ FastAPI backend running on Uvicorn
📱 Real-time scam alerts delivered to user’s WhatsApp
🏗️ Architecture

            ┌────────────────────────┐
            │        User            │
            │  (WhatsApp Message)    │
            └──────────┬─────────────┘
                       │
                       ▼
            ┌────────────────────────┐
            │   Twilio WhatsApp API  │
            │  (Message Webhook)     │
            └──────────┬─────────────┘
                       │
                       ▼
            ┌────────────────────────┐
            │   FastAPI Backend      │
            │ (Webhook on Uvicorn)   │
            └──────────┬─────────────┘
                       │
  ┌────────────────────┼─────────────────────┐
  │                    │                     │
  ▼                    ▼                     ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────────┐ │ Vertex AI │ │ Trusted Src │ │ Firestore (NoSQL)│ │ (Gemini LLM │ │ Checker │ │ Logs all msgs │ │ Classifier)│ │ (SEBI/RBI/BSE) │ │ └──────┬──────┘ └──────┬──────┘ └──────────┬──────┘ │ │ │ └─────────────┬─────┴────────────────────────┘ ▼ ┌───────────────┐ │ BigQuery │ │ (Analytics / │ │ Dashboards) │ └───────────────┘

                       │
                       ▼
            ┌────────────────────────┐
            │ Twilio MessagingReply  │
            │  (Scam/Warning/Legit)  │
            └──────────┬─────────────┘
                       │
                       ▼
            ┌────────────────────────┐
            │        User            │
            │ (Receives Response)    │
            └────────────────────────┘
Run the server uvicorn app.main:app --reload --port 8080

Set the Webhook URL to your running FastAPI endpoint:

https://your-ngrok-url/webhook

Send a WhatsApp message to test

📌 Tech Stack

Backend: FastAPI + Uvicorn

AI Models: Google Vertex AI (Gemini 2.0 Flash)

Messaging: Twilio WhatsApp API

Database: Firestore (NoSQL)

Analytics: BigQuery

Deployment: Local / Cloud Run

🎯 Future Enhancements

Multi-language support (Hindi, Kannada, Tamil, etc.)

Image/Screenshot OCR + scam detection

Browser extension for financial news verification
