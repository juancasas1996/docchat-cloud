"""Simulated agentic RAG workflow: router -> investigator -> drafter <-> critic.

The retrieval is FAKE and scripted: the first search always returns irrelevant
law fragments, forcing the investigator (a real ReAct agent) to genuinely judge
them insufficient and rewrite the query; the second search returns relevant
(invented, clearly marked) fragments. Every decision — routing, judging,
rewriting, drafting, critique — is a real LLM decision over fake data.
Didactic scaffolding for the real AI Search retrieval that replaces the tool later.
"""

import operator
from functools import lru_cache
from typing import Annotated, TypedDict

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import create_react_agent

from .react_agent import LLM_API_KEY, LLM_BASE_URL, REACT_MODEL

MAX_CRITIC_ROUNDS = 2
MAX_SEARCHES = 3

# --------------------------------------------------------------------------
# Fake corpus (clearly simulated). First batch: irrelevant on purpose.
# --------------------------------------------------------------------------

BAD_CHUNKS = [
    ("Ley Simulada 84, Art. 45", "Los permisos de pesca deportiva en embalses "
     "públicos tendrán vigencia de un año y deberán renovarse ante la autoridad "
     "ambiental competente."),
    ("Decreto Simulado 210, Art. 12", "El nivel máximo de ruido permitido en "
     "zonas residenciales entre las 22:00 y las 6:00 será de 45 decibeles."),
    ("Estatuto Simulado Tributario, Art. 7", "El impuesto predial unificado se "
     "liquidará sobre el avalúo catastral vigente a primero de enero de cada año."),
]

GOOD_CHUNKS = [
    ("Ley Simulada 769, Art. 152", "Quien conduzca bajo el influjo del alcohol "
     "será sancionado según el grado de alcoholemia: entre 20 y 39 mg de etanol "
     "por 100 ml de sangre constituye primer grado; entre 40 y 99 mg, segundo "
     "grado; 100 mg o más, tercer grado."),
    ("Ley Simulada 769, Art. 131", "La conducción en primer grado de embriaguez "
     "acarrea multa de noventa (90) salarios mínimos diarios, suspensión de la "
     "licencia por un (1) año e inmovilización del vehículo."),
    ("Ley Simulada 1696, Art. 5", "En caso de reincidencia en conducción en "
     "estado de embriaguez, procederá la cancelación definitiva de la licencia "
     "de conducción y multa de hasta mil ochenta (1.080) salarios mínimos diarios."),
]


def _format_chunks(chunks) -> str:
    return "\n\n".join(f"[{ref}] {text}" for ref, text in chunks)


def _make_fake_search(log: list):
    """Scripted retrieval: call #1 -> bad batch, later calls -> good batch."""
    calls = {"n": 0}

    @tool
    def search_docs(query: str) -> str:
        """Busca en la base normativa y devuelve los 3 fragmentos más relevantes."""
        calls["n"] += 1
        batch = BAD_CHUNKS if calls["n"] == 1 else GOOD_CHUNKS
        log.append(f"🔎 búsqueda #{calls['n']}: «{query}»")
        return _format_chunks(batch)

    return search_docs


# --------------------------------------------------------------------------
# Workflow state and nodes
# --------------------------------------------------------------------------

class RagState(TypedDict):
    question: str
    route: str
    evidence: str
    draft: str
    critique: str
    rounds: int
    trace: Annotated[list[str], operator.add]  # reducer: cada nodo AGREGA sus entradas


@lru_cache(maxsize=1)
def _llm() -> ChatOpenAI:
    return ChatOpenAI(
        base_url=LLM_BASE_URL, api_key=LLM_API_KEY, model=REACT_MODEL, temperature=0
    )


def _ask(prompt: str) -> str:
    return (_llm().invoke(prompt).content or "").strip()


def _router(state: RagState) -> dict:
    label = _ask(
        "Clasifica la pregunta del usuario. Responde ÚNICAMENTE una etiqueta:\n"
        "- RAG: pregunta sobre leyes, normas o regulaciones (requiere buscar documentos)\n"
        "- NO_RAG: cualquier otra cosa (saludos, matemáticas, cultura general)\n\n"
        f"Pregunta: {state['question']}"
    ).upper()
    route = "RAG" if "NO_RAG" not in label else "NO_RAG"
    return {"route": route, "trace": [f"🚦 router: {route}"]}


def _direct_answer(state: RagState) -> dict:
    answer = _ask(
        "Responde breve y amablemente (esta pregunta no requiere buscar en "
        f"documentos normativos): {state['question']}"
    )
    return {"draft": answer, "trace": ["💬 respuesta directa (sin RAG)"]}


def _investigate(state: RagState) -> dict:
    searches: list[str] = []
    agent = create_react_agent(
        _llm(),
        [_make_fake_search(searches)],
        prompt=(
            "Eres un investigador documental. Tu trabajo es reunir EVIDENCIA, "
            "NUNCA responder la pregunta. Usa search_docs con una query de "
            "palabras clave. Evalúa si los fragmentos devueltos son relevantes "
            "a la pregunta: si NO lo son, reformula la query con términos "
            f"distintos y busca de nuevo (máximo {MAX_SEARCHES} búsquedas). "
            "Al terminar responde SOLO con:\n"
            "EVIDENCIA:\n[copia textual de los fragmentos relevantes con sus referencias]\n"
            "o exactamente 'NO PUEDO RESPONDER' si nada fue relevante."
        ),
    )
    result = agent.invoke(
        {"messages": [("user", f"Reúne evidencia para: {state['question']}")]}
    )
    evidence = result["messages"][-1].content
    trace = searches + [
        f"⚖️ juicio del investigador tras búsqueda #1: fragmentos irrelevantes → reescribió la query"
        if len(searches) > 1
        else "⚖️ investigador: primera búsqueda suficiente",
        f"📚 evidencia entregada ({len(evidence)} caracteres)",
    ]
    return {"evidence": evidence, "trace": trace}


def _draft(state: RagState) -> dict:
    feedback = (
        f"\n\nUn revisor rechazó tu intento anterior:\n{state['draft']}\n"
        f"Comentarios del revisor: {state['critique']}\nCorrige la respuesta."
        if state.get("critique") and "APROBADO" not in state["critique"]
        else ""
    )
    draft = _ask(
        "Redacta una respuesta clara para el usuario usando SOLO la evidencia. "
        "Cita las referencias entre corchetes. Si la evidencia dice 'NO PUEDO "
        "RESPONDER', dilo honestamente.\n\n"
        f"Pregunta: {state['question']}\n\nEvidencia:\n{state['evidence']}{feedback}"
    )
    return {
        "draft": draft,
        "rounds": state["rounds"] + 1,
        "trace": [f"✍️ redactor: borrador #{state['rounds'] + 1}"],
    }


def _critic(state: RagState) -> dict:
    verdict = _ask(
        "Eres un revisor estricto. Evalúa si la respuesta (1) se sostiene "
        "SOLO en la evidencia, (2) responde la pregunta, (3) cita referencias. "
        "Responde 'APROBADO' o, si falla algo, comentarios concretos en 1-2 líneas.\n\n"
        f"Pregunta: {state['question']}\n\nEvidencia:\n{state['evidence']}\n\n"
        f"Respuesta a evaluar:\n{state['draft']}"
    )
    ok = "APROBADO" in verdict.upper()
    return {
        "critique": verdict,
        "trace": [f"🧐 crítico: {'APROBADO ✅' if ok else f'rechazado → {verdict[:80]}'}"],
    }


def _after_router(state: RagState) -> str:
    return "investigate" if state["route"] == "RAG" else "direct"


def _after_critic(state: RagState) -> str:
    approved = "APROBADO" in state["critique"].upper()
    return END if approved or state["rounds"] >= MAX_CRITIC_ROUNDS else "draft"


@lru_cache(maxsize=1)
def _workflow():
    g = StateGraph(RagState)
    g.add_node("router", _router)
    g.add_node("direct", _direct_answer)
    g.add_node("investigate", _investigate)
    g.add_node("draft", _draft)
    g.add_node("critic", _critic)
    g.set_entry_point("router")
    g.add_conditional_edges("router", _after_router, {"investigate": "investigate", "direct": "direct"})
    g.add_edge("direct", END)
    g.add_edge("investigate", "draft")
    g.add_edge("draft", "critic")
    g.add_conditional_edges("critic", _after_critic, {"draft": "draft", END: END})
    return g.compile()


def run_rag(question: str) -> dict:
    final = _workflow().invoke(
        RagState(question=question, route="", evidence="", draft="", critique="", rounds=0, trace=[])
    )
    return {"answer": final["draft"], "trace": final["trace"], "model": REACT_MODEL}
