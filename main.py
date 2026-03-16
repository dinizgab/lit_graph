from dotenv import load_dotenv
load_dotenv()

import asyncio
import streamlit as st
from src.graph.graph import build_graph
from src.graph.state import LitGraphState
from langsmith import traceable


NODE_LABELS = {
    "supervisor":  "Interpretando sua pergunta...",
    "retriever":   "Buscando referências no livro...",
    "automation":  "Gerando guia de estudo...",
    "safety":      "Verificando conteúdo...",
    "answerer":    "Redigindo resposta...",
    "self_check":  "Verificando evidências...",
    "output":      "Finalizando...",
    "refuse":      "Processando...",
}


st.set_page_config(
    page_title="LitGraph",
    page_icon="📖",
    layout="centered",
)
 
@st.cache_resource
def get_graph():
    return build_graph()

@traceable(name="litgraph_run")
async def run_graph(graph, state):
    return await graph.ainvoke(state)
 
graph = get_graph()
 
with st.sidebar:
    st.title("📖 LitGraph")
    st.caption("Q&A e guias de estudo sobre obras clássicas do domínio público.")
    st.divider()
 
    student_level = st.selectbox(
        "Nível do leitor",
        options=["fundamental", "medio", "superior", "curioso"],
        format_func=lambda x: {
            "fundamental": "Ensino Fundamental",
            "medio": "Ensino Médio",
            "superior": "Ensino Superior",
            "curioso": "Leitor Curioso",
        }[x],
        index=1,
    )
 
    st.divider()
    st.markdown("**Exemplos**")
    examples = [
        "Quem é Capitu?",
        "Gere um guia de Crime e Castigo",
        "Temas de A Divina Comédia",
        "Gere um guia de Dom Quixote",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True, key=ex):
            st.session_state.messages.append({"role": "user", "content": ex})
            st.rerun()
 
    st.divider()
    if st.button("🗑 Limpar conversa", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
 
st.title("LitGraph")
 
if "messages" not in st.session_state:
    st.session_state.messages = []
 
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Pergunte sobre uma obra ou peça um guia de estudo…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        initial_state = LitGraphState({
            "user_query": prompt,
            "book_title": "",
            "student_level": student_level if student_level in ("fundamental", "medio", "superior", "curioso") else "curioso",
            "self_check_attempts": 0,
            "enable_self_check": True,
        })

        result = [None]

        with st.status("Consultando as fontes…", expanded=True) as status:
            async def stream():
                
                async for event in graph.astream_events(initial_state, version="v2"):
                    if event["event"] == "on_chain_start":
                        node = event.get("name", "")
                        if node in NODE_LABELS:
                            status.update(label=NODE_LABELS[node])
                    elif event["event"] == "on_chain_end" and event.get("name") == "LangGraph":
                        output = event.get("data", {}).get("output", {})
                        result[0] = output.get("final_answer") or output.get("error", "Sem resposta.")

            asyncio.run(stream())
            status.update(label="Pronto!", state="complete", expanded=False)

        st.markdown(result[0])

    st.session_state.messages.append({"role": "assistant", "content": result[0]})
    