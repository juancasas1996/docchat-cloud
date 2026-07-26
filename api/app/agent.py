"""Minimal agentic workflow: triage -> answer -> verify (with one retry).

Each node gives the LLM ONE narrow task with a strict output format, so a
small fast model (llama-3.1-8b on NVIDIA's free tier) is enough. Unlike the
original IBM DocChat lab, the verify loop is capped: a failed verification
retries the answer at most MAX_RETRIES times instead of looping forever.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, StateGraph
from openai import OpenAI

NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
CHAT_MODEL = os.getenv("NVIDIA_CHAT_MODEL", "meta/llama-3.1-8b-instruct")
MAX_RETRIES = 1

ABSTAIN_ANSWER = (
    "I can't answer that from the provided context. "
    "Try asking about the DocChat Cloud project (architecture, CI/CD, agent, roadmap)."
)

SAMPLE_CONTEXT = (Path(__file__).parent / "sample_context.md").read_text()


class AgentState(TypedDict):
    question: str
    context: str
    draft_answer: str
    verification: str
    can_answer: bool
    retries: int


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    return OpenAI(base_url=NVIDIA_BASE_URL, api_key=os.environ["NVIDIA_API_KEY"])


def _llm(prompt: str, max_tokens: int, temperature: float = 0.0) -> str:
    response = _client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()


def _triage(state: AgentState) -> dict:
    label = _llm(
        f"""You are a relevance checker between a user's question and a document.
Respond with ONLY one label and nothing else:
- CAN_ANSWER: the document contains enough information to answer.
- PARTIAL: the document discusses the topic but not every detail.
- NO_MATCH: the document does not discuss the topic at all.

Question: {state['question']}
Document:
{state['context']}""",
        max_tokens=10,
    ).upper()
    can_answer = label in {"CAN_ANSWER", "PARTIAL"}
    return {
        "can_answer": can_answer,
        "draft_answer": "" if can_answer else ABSTAIN_ANSWER,
    }


def _answer(state: AgentState) -> dict:
    draft = _llm(
        f"""Answer the question using ONLY the context below.
Be clear, concise and factual. If the context is insufficient, say so.

Question: {state['question']}
Context:
{state['context']}""",
        max_tokens=600,
        temperature=0.2,
    )
    return {"draft_answer": draft, "retries": state["retries"] + 1}


def _verify(state: AgentState) -> dict:
    report = _llm(
        f"""Verify the answer against the context. Respond EXACTLY in this format:
Supported: YES/NO
Unsupported Claims: [comma-separated list, or empty]
Notes: [one short sentence]

Answer: {state['draft_answer']}
Context:
{state['context']}""",
        max_tokens=300,
    )
    return {"verification": report}


def _after_triage(state: AgentState) -> str:
    return "answer" if state["can_answer"] else END


def _after_verify(state: AgentState) -> str:
    failed = "Supported: NO" in state["verification"]
    return "answer" if failed and state["retries"] <= MAX_RETRIES else END


@lru_cache(maxsize=1)
def _workflow():
    graph = StateGraph(AgentState)
    graph.add_node("triage", _triage)
    graph.add_node("answer", _answer)
    graph.add_node("verify", _verify)
    graph.set_entry_point("triage")
    graph.add_conditional_edges("triage", _after_triage, {"answer": "answer", END: END})
    graph.add_edge("answer", "verify")
    graph.add_conditional_edges("verify", _after_verify, {"answer": "answer", END: END})
    return graph.compile()


def run_agent(question: str, context: str | None = None) -> dict:
    """Run the workflow; with no context, answers about the project itself."""
    final = _workflow().invoke(
        AgentState(
            question=question,
            context=context or SAMPLE_CONTEXT,
            draft_answer="",
            verification="",
            can_answer=False,
            retries=0,
        )
    )
    return {
        "answer": final["draft_answer"],
        "verification": final["verification"],
        "model": CHAT_MODEL,
    }
