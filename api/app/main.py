from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="DocChat Cloud API",
    description="Backend for an agentic RAG chat over documents.",
    version="0.1.0",
)


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    # Placeholder: the agentic RAG pipeline (retriever + LangGraph agents)
    # replaces this echo in a later phase.
    return ChatResponse(answer=f"You asked: {payload.question}")
