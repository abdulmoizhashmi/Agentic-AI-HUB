from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Optional
from dotenv import load_dotenv
from pathlib import Path
import os
import logging
from .workflow import AgentOrchestrator
from .storage import SessionStore

logger = logging.getLogger(__name__)
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
app = FastAPI(title="Agentic AI Hub API", version="1.0.0",
              description="Customer Support and AI Interview agents with workflow traces.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
store = SessionStore(Path(__file__).resolve().parents[1] / "data" / "sessions.json")
orchestrator = AgentOrchestrator(store)

class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    agent: Literal["support", "interview"]
    message: str = Field(min_length=1, max_length=6000)
    role: Optional[str] = "Software Engineer"
    difficulty: Optional[Literal["beginner", "intermediate", "advanced"]] = "intermediate"

@app.get("/")
def root():
    return {"name": "Agentic AI Hub API", "status": "ok", "docs": "/docs"}

@app.get("/api/health")
def health():
    return {"status": "ok", "llm_enabled": bool(os.getenv("OPENAI_API_KEY"))}

@app.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        return await orchestrator.run(req.model_dump())
    except Exception as exc:
        logger.exception("Agent workflow failed.")
        raise HTTPException(status_code=500, detail="Agent workflow failed. Check the backend logs.") from exc

@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    return store.get_session(session_id)

@app.delete("/api/sessions/{session_id}")
def clear_session(session_id: str):
    store.clear_session(session_id)
    return {"ok": True, "session_id": session_id}

@app.get("/api/human-review")
def human_review_queue():
    return store.pending_reviews()
