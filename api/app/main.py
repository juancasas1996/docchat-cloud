import logging
import os

from fastapi import FastAPI
from pydantic import BaseModel

from .agent import run_agent

logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="DocChat Cloud API",
    description="Backend for an agentic RAG chat over documents.",
    version="0.2.0",
)


class ChatRequest(BaseModel):
    question: str
    context: str | None = None


class ChatResponse(BaseModel):
    answer: str
    verification: str = ""
    model: str = ""


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "agent_ready": bool(os.getenv("NVIDIA_API_KEY"))}


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    if not os.getenv("NVIDIA_API_KEY"):
        return ChatResponse(
            answer="The agent has no model credentials yet (NVIDIA_API_KEY is not set)."
        )
    try:
        result = run_agent(payload.question, payload.context)
    except Exception:
        logger.exception("Agent workflow failed")
        return ChatResponse(answer="The agent hit an error talking to the model. Try again.")
    return ChatResponse(**result)
