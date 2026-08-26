# Company AI Chatbot — Backend

FastAPI service for the company chatbot. Talks to Gemini for LLM responses.
Runs independently from the existing PHP website; communicates over HTTPS.

## Setup

```bash
python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file in the project root:

GEMINI_API_KEY=your-actual-key-here

## Run

```bash
uvicorn app.main:app --reload
```

Service runs at `http://localhost:8000`.
Interactive API docs: `http://localhost:8000/docs`.

## Endpoints

- `GET /health` — liveness check
- `POST /chat` — send `{"message": "..."}`, returns `{"reply": "..."}`

## Try it

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"message\": \"hello\"}"
```

## Project layout

app/
├── main.py FastAPI app, CORS, router registration
├── api/
│ ├── health.py GET /health
│ └── chat.py POST /chat
├── core/
│ └── logging_config.py Logging setup
├── services/
│ └── llm_service.py Gemini API call, isolated here
└── schemas/
└── chat.py Request/response models


## Notes

- CORS currently only allows `http://localhost:3000` — update `app/main.py`
  once the real PHP site domain is known.
- Not yet built: MySQL persistence, RAG, conversation memory, business
  tools, authentication, admin knowledge base, human handoff.