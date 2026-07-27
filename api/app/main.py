import logging
import os

from fastapi import FastAPI
from pydantic import BaseModel

from . import react_agent
from .agent import run_agent
from .react_agent import run_react

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


class ReactRequest(BaseModel):
    question: str


class ReactResponse(BaseModel):
    answer: str
    trace: list[str] = []
    model: str = ""


@app.post("/api/react", response_model=ReactResponse)
async def react(payload: ReactRequest) -> ReactResponse:
    if not react_agent.LLM_API_KEY:
        return ReactResponse(
            answer="The agent has no model credentials yet (set OPENAI_API_KEY or LLM_API_KEY)."
        )
    try:
        result = await run_react(payload.question)
    except Exception:
        logger.exception("ReAct agent failed")
        return ReactResponse(
            answer="The agent hit an error talking to the model or the MCP server. Try again."
        )
    return ReactResponse(**result)


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
