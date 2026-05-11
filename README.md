# Decision Minds — Meeting Intelligence Platform

AI-powered meeting video analysis — transcribe meetings and extract per-person action items, Google Meet + Docs style, using SharePoint links and Groq's ultra-fast LPU inference.

## Quick Start (Docker)

```bash
# 1. Add your Groq API key (free at https://console.groq.com)
cp .env.example .env
# Edit .env → set GROQ_API_KEY=your_key

# 2. Start
docker compose up -d

# 3. Open http://localhost:3000
```

## What It Does

1. **Paste a SharePoint link** (or upload a video file)
2. **Groq LPU** transcribes at 50x realtime (Whisper Large v3 Turbo)
3. **Groq Llama 3.3 70B** extracts structured action items per person
4. **Export** results as JSON or back to SharePoint

Each action item includes: owner, task, deadline, priority, confidence score, and supporting context from the transcript.

## Requirements

- Docker Desktop
- Groq API key (free tier at [console.groq.com](https://console.groq.com))
- Optional: Azure AD app registration for SharePoint integration

## Without Docker

```bash
# Backend
pip install -r requirements.txt
python -m backend.main

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## SharePoint Setup (Optional)

1. Register an app in Azure AD → API Permissions → Microsoft Graph
2. Add `Sites.Read.All` and `Files.ReadWrite.All`
3. Set `MS_CLIENT_ID`, `MS_CLIENT_SECRET`, `MS_TENANT_ID` in `.env`
