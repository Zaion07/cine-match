from __future__ import annotations

import os

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from movie_service import MovieAPIError, TMDbClient, build_recommendation, format_movies


QUESTIONS = [
    "Qual gênero você quer?",
    "Você prefere um filme leve, engraçado, emocionante ou mais intenso?",
    "Tem alguma década ou ano em mente?",
    "Quer citar algum filme parecido ou algo que você já gostou?",
]


def load_api_key() -> str:
    try:
        return str(st.secrets["TMDB_API_KEY"]).strip()
    except (KeyError, StreamlitSecretNotFoundError):
        pass
    return os.getenv("TMDB_API_KEY", "").strip()


def get_client() -> TMDbClient:
    api_key = load_api_key()
    if not api_key:
        st.error("Configure a variável de ambiente TMDB_API_KEY antes de abrir o app.")
        st.stop()
    return TMDbClient(api_key)


def init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Oi! Vou te fazer 4 perguntas rápidas para recomendar melhor.",
            }
        ]
    if "step" not in st.session_state:
        st.session_state.step = 0
    if "answers" not in st.session_state:
        st.session_state.answers = []
    if "filters" not in st.session_state:
        st.session_state.filters = {}
    if "completed" not in st.session_state:
        st.session_state.completed = False


def reset_flow() -> None:
    st.session_state.step = 0
    st.session_state.answers = []
    st.session_state.filters = {}
    st.session_state.completed = False
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Oi! Vou te fazer 4 perguntas rápidas para recomendar melhor.",
        }
    ]


def render_message(message: dict[str, str]) -> None:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


def current_question() -> str | None:
    if st.session_state.step < len(QUESTIONS):
        return QUESTIONS[st.session_state.step]
    return None


def compose_search_message(answers: list[str]) -> str:
    labels = ["gênero", "clima", "ano", "referência"]
    return " | ".join(f"{label}: {answer}" for label, answer in zip(labels, answers))


def main() -> None:
    st.set_page_config(page_title="CineMatch", page_icon="🎬", layout="centered")
    st.title("CineMatch")
    st.caption("Chatbot de indicação de filmes conectado à API da TMDb.")

    init_state()
    client = get_client()

    if st.button("Recomeçar conversa"):
        reset_flow()
        st.rerun()

    for message in st.session_state.messages:
        render_message(message)

    if st.session_state.completed:
        st.success("Se quiser, clique em 'Recomeçar conversa' para nova rodada.")
        return

    question = current_question()
    if question:
        st.chat_message("assistant").markdown(question)

    user_message = st.chat_input("Digite sua resposta")
    if not user_message:
        return

    st.session_state.messages.append({"role": "user", "content": user_message})
    render_message(st.session_state.messages[-1])

    st.session_state.answers.append(user_message)
    st.session_state.step += 1

    if st.session_state.step < len(QUESTIONS):
        st.session_state.messages.append({"role": "assistant", "content": "Pronto. Vamos para a próxima."})
        render_message(st.session_state.messages[-1])
        st.rerun()

    search_message = compose_search_message(st.session_state.answers)
    try:
        result = build_recommendation(search_message, client, st.session_state.filters)
    except MovieAPIError as exc:
        st.session_state.messages.append({"role": "assistant", "content": f"Não consegui buscar os filmes: {exc}"})
        render_message(st.session_state.messages[-1])
        return

    st.session_state.filters = result["filters"]
    assistant_text = f"{result['reply']}\n\n{format_movies(result['movies'])}"
    st.session_state.messages.append({"role": "assistant", "content": assistant_text})
    render_message(st.session_state.messages[-1])
    st.session_state.completed = True


if __name__ == "__main__":
    main()
