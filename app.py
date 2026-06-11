from __future__ import annotations

import os

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from movie_service import MovieAPIError, TMDbClient, build_recommendation, format_movies


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
                "content": "Oi! Me diga um gênero, ano ou título de filme e eu te passo recomendações.",
            }
        ]
    if "filters" not in st.session_state:
        st.session_state.filters = {}


def render_message(message: dict[str, str]) -> None:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


def main() -> None:
    st.set_page_config(page_title="CineMatch", page_icon="🎬", layout="centered")
    st.title("CineMatch")
    st.caption("Chatbot de indicação de filmes conectado à API da TMDb.")

    init_state()
    client = get_client()

    for message in st.session_state.messages:
        render_message(message)

    user_message = st.chat_input("Ex.: quero um filme de terror dos anos 90")
    if not user_message:
        return

    st.session_state.messages.append({"role": "user", "content": user_message})
    render_message(st.session_state.messages[-1])

    try:
        result = build_recommendation(user_message, client, st.session_state.filters)
    except MovieAPIError as exc:
        assistant_message = f"Não consegui buscar os filmes: {exc}"
        st.session_state.messages.append({"role": "assistant", "content": assistant_message})
        render_message(st.session_state.messages[-1])
        return

    st.session_state.filters = result["filters"]
    assistant_text = f"{result['reply']}\n\n{format_movies(result['movies'])}"
    st.session_state.messages.append({"role": "assistant", "content": assistant_text})
    render_message(st.session_state.messages[-1])


if __name__ == "__main__":
    main()
