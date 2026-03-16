from dotenv import load_dotenv
load_dotenv()

import asyncio
import streamlit as st
from src.graph.graph import build_graph
from src.graph.state import LitGraphState
from langsmith import traceable

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
        with st.spinner("Consultando as fontes…"):
            initial_state = LitGraphState({
                "user_query": prompt,
                "book_title": "",
                "student_level": student_level if student_level in ("fundamental", "medio", "superior", "curioso") else "curioso",
                "self_check_attempts": 0,
                "enable_self_check": True
            })
            result = asyncio.run(run_graph(graph, initial_state))
            final = result.get("final_answer") or result.get("error", "Sem resposta.")

        st.markdown(final)

    st.session_state.messages.append({"role": "assistant", "content": final})