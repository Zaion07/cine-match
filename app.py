from __future__ import annotations

import os

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from movie_service import Movie, MovieAPIError, TMDbClient, build_recommendation

QUESTIONS = [
    ("Qual genero voce quer assistir?",
     "Ex: acao, drama, comedia, terror, romance, ficcao cientifica, animacao..."),
    ("Como voce quer se sentir assistindo?",
     "Ex: empolgado, reflexivo, leve, assustado, emocionado, epico..."),
    ("Vai assistir sozinho, em casal ou em familia?",
     "Isso ajuda a calibrar o tipo de filme ideal"),
    ("Tem alguma epoca ou ano preferido?",
     "Ex: anos 80, anos 90, classico, recente, 2020+ — ou tanto faz"),
    ("Prefere filme de qual origem?",
     "Ex: brasileiro, americano, europeu, japones, coreano — ou tanto faz"),
    ("Prefere filmes curtos (ate 1h30) ou longos (mais de 2h)?",
     "Ex: curto e objetivo, longo e epico — ou tanto faz"),
    ("Quer algo aclamado pela critica ou um grande sucesso de publico?",
     "Ex: Oscar, Cannes, festivais — ou blockbuster, popular, bilheteria"),
    ("Cita um filme que voce amou:",
     "Ex: Inception, Parasita, O Poderoso Chefao — ou 'nenhum'"),
    ("Tem algum ator, atriz ou diretor favorito?",
     "Ex: Meryl Streep, Nolan, Tarantino — ou 'nenhum'"),
    ("Tem algum tema ou elemento especial que quer na historia?",
     "Ex: viagem no tempo, vinganca, heist, sobrevivencia, espionagem..."),
]

GENRE_COLORS: dict[str, str] = {
    "Action":          "#E50914",
    "Adventure":       "#FF6B35",
    "Animation":       "#FFD700",
    "Comedy":          "#F5C518",
    "Crime":           "#C0392B",
    "Documentary":     "#4A90D9",
    "Drama":           "#8E44AD",
    "Family":          "#27AE60",
    "Fantasy":         "#A29BFE",
    "History":         "#E67E22",
    "Horror":          "#9B59B6",
    "Music":           "#FD79A8",
    "Mystery":         "#636E72",
    "Romance":         "#FF69B4",
    "Science Fiction": "#00CEC9",
    "Thriller":        "#E17055",
    "War":             "#74B9FF",
    "Western":         "#B8860B",
}

CINEMA_CSS = """
<style>
@keyframes shimmer {
    0%   { background-position: -200% center; }
    100% { background-position:  200% center; }
}
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes float {
    0%, 100% { transform: translateY(0); }
    50%       { transform: translateY(-5px); }
}

/* base */
html, body, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(ellipse at 15% 30%, #220028 0%, transparent 55%),
        radial-gradient(ellipse at 85% 10%, #0d1a3a 0%, transparent 55%),
        radial-gradient(ellipse at 50% 85%, #1a0015 0%, transparent 55%),
        #07070f !important;
}
[data-testid="stHeader"] { background: transparent !important; }

/* sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #09091a 0%, #0c0c20 100%) !important;
    border-right: 1px solid #E5091425 !important;
}
[data-testid="stSidebar"] p { color: #9999bb !important; font-size: 0.875rem; }

/* chat messages */
[data-testid="stChatMessage"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 16px !important;
    margin-bottom: 8px !important;
    animation: fadeInUp 0.3s ease both;
}

/* chat input */
[data-testid="stChatInput"] > div {
    border: 1.5px solid #E50914 !important;
    border-radius: 14px !important;
    background: rgba(229,9,20,0.05) !important;
}

/* buttons */
.stButton > button {
    background: linear-gradient(135deg, #E50914 0%, #b20710 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 0.3px !important;
    box-shadow: 0 4px 18px #E5091440 !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 28px #E5091460 !important;
}

/* progress */
[data-testid="stProgress"] > div > div {
    background: linear-gradient(90deg, #E50914, #FF6B35, #F5C518) !important;
    border-radius: 999px !important;
}
[data-testid="stProgress"] > div {
    background: rgba(255,255,255,0.07) !important;
    border-radius: 999px !important;
}

hr { border-color: #E5091420 !important; }

[data-testid="stExpander"] {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid #2a2a4a !important;
    border-radius: 10px !important;
}
</style>
"""

HEADER_HTML = """
<div style="margin-bottom:24px; animation: fadeInUp 0.4s ease both;">
    <div style="
        font-size:2.8rem; font-weight:900; letter-spacing:-1px; line-height:1;
        background: linear-gradient(135deg, #E50914 0%, #FF6B35 35%, #F5C518 65%, #E50914 100%);
        background-size: 200% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: shimmer 4s linear infinite;
        display: inline-block;
    ">CineMatch</div>
    <div style="color:#7777aa; font-size:1rem; margin-top:6px; font-weight:400;">
        Seu guia pessoal para encontrar o filme perfeito
    </div>
</div>
"""

GRADIENT_LINE_HTML = """
<div style="
    height:3px;
    background: linear-gradient(90deg, #E50914, #FF6B35, #F5C518, #E50914);
    background-size: 200% auto;
    border-radius: 2px;
    margin-bottom: 28px;
    animation: shimmer 4s linear infinite;
"></div>
"""

NOW_SHOWING_HTML = """
<div style="
    display:inline-flex; align-items:center; gap:8px;
    background: linear-gradient(135deg, #E50914 0%, #b20710 100%);
    color:white; padding:6px 18px; border-radius:999px;
    font-size:0.75rem; font-weight:800; letter-spacing:2.5px;
    text-transform:uppercase; margin-bottom:20px;
    box-shadow: 0 4px 18px #E5091450;
">
    <span style="
        width:7px; height:7px; border-radius:50%;
        background:#fff; display:inline-block;
        animation: float 1s ease-in-out infinite;
    "></span>
    NOW SHOWING
</div>
"""


def load_api_key() -> str:
    try:
        return str(st.secrets["TMDB_API_KEY"]).strip()
    except (KeyError, StreamlitSecretNotFoundError):
        pass
    return os.getenv("TMDB_API_KEY", "").strip()


def get_client() -> TMDbClient:
    api_key = load_api_key()
    if not api_key:
        st.error("Configure a variavel TMDB_API_KEY antes de abrir o app.")
        st.stop()
    return TMDbClient(api_key)


def _first_question_msg() -> str:
    q, hint = QUESTIONS[0]
    return f"**{q}**\n\n*{hint}*"


def init_state() -> None:
    defaults: dict = {
        "messages": [
            {
                "role": "assistant",
                "content": (
                    "Ola! Eu sou o **CineMatch**.\n\n"
                    "Vou te fazer **10 perguntas rapidas** e encontrar os **3 filmes perfeitos** para o seu momento."
                ),
            },
            {"role": "assistant", "content": _first_question_msg()},
        ],
        "step": 0,
        "answers": [],
        "completed": False,
        "movies": [],
        "reply": "",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def reset_flow() -> None:
    for key in ("step", "answers", "completed", "movies", "reply", "messages"):
        st.session_state.pop(key, None)
    init_state()


def render_message(message: dict[str, str]) -> None:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


def _genre_tag(genre: str) -> str:
    color = GENRE_COLORS.get(genre, "#555577")
    return (
        f'<span style="background:{color}20;color:{color};border:1px solid {color}55;'
        f'border-radius:6px;padding:3px 10px;font-size:0.7rem;font-weight:700;'
        f'margin:2px;display:inline-block;letter-spacing:0.3px">{genre}</span>'
    )


def _rating_stars(rating: float | None) -> str:
    if not rating:
        return "☆☆☆☆☆"
    full = round(rating / 2)
    return "★" * full + "☆" * (5 - full)


def render_movie_card(movie: Movie, rank: int = 1) -> None:
    poster_url = movie.poster_url("w500")
    rating_val = f"{movie.rating:.1f}" if movie.rating else "N/A"
    stars = _rating_stars(movie.rating)
    votes = f"{movie.vote_count:,}" if movie.vote_count else "?"
    genre_tags = "".join(_genre_tag(g) for g in (movie.genres or [])[:4])
    overview = (movie.overview[:260] + "...") if len(movie.overview) > 260 else movie.overview

    rank_configs = {
        1: ("#F5C518", "#000", "#1 TOP PICK", "0 0 30px #F5C51820, 0 8px 32px rgba(0,0,0,0.6)"),
        2: ("#C0C0C0", "#000", "#2",           "0 8px 24px rgba(0,0,0,0.5)"),
        3: ("#CD7F32", "#000", "#3",           "0 8px 24px rgba(0,0,0,0.5)"),
    }
    badge_color, badge_text_color, badge_label, card_shadow = rank_configs.get(
        rank, ("#fff", "#000", f"#{rank}", "0 8px 24px rgba(0,0,0,0.5)")
    )
    border_color = "#F5C518" if rank == 1 else "#E5091430" if rank == 2 else "#2a2a4a"

    badge_html = (
        f'<div style="position:absolute;top:12px;left:12px;z-index:10;'
        f'background:{badge_color};color:{badge_text_color};border-radius:8px;'
        f'padding:4px 10px;font-size:0.68rem;font-weight:900;letter-spacing:1px;'
        f'box-shadow:0 2px 8px rgba(0,0,0,0.5)">'
        f'{badge_label}</div>'
    )

    rating_badge = (
        f'<div style="position:absolute;bottom:12px;right:12px;'
        f'background:rgba(245,197,24,0.93);color:#000;border-radius:8px;'
        f'padding:4px 10px;font-weight:800;font-size:0.85rem;backdrop-filter:blur(4px)">'
        f'{rating_val}/10</div>'
    )

    if poster_url:
        poster_html = (
            f'<div style="position:relative">'
            f'  {badge_html}'
            f'  <img src="{poster_url}" alt="{movie.title}"'
            f'    style="width:100%;aspect-ratio:2/3;object-fit:cover;display:block;border-radius:12px 12px 0 0">'
            f'  <div style="position:absolute;bottom:0;left:0;right:0;height:50%;'
            f'    background:linear-gradient(transparent,#0a0a14);pointer-events:none"></div>'
            f'  {rating_badge}'
            f'</div>'
        )
    else:
        poster_html = (
            f'<div style="position:relative;width:100%;aspect-ratio:2/3;'
            f'background:linear-gradient(135deg,#1a1a3e,#0a0a1a);'
            f'display:flex;align-items:center;justify-content:center;'
            f'border-radius:12px 12px 0 0;font-size:3rem;color:#333">'
            f'  {badge_html}'
            f'  [ sem poster ]'
            f'  {rating_badge}'
            f'</div>'
        )

    delay = 0.1 + rank * 0.1

    card_html = f"""
<div style="
    background: linear-gradient(180deg, #12122a 0%, #0a0a18 100%);
    border-radius: 14px; overflow: hidden;
    border: 1px solid {border_color};
    box-shadow: {card_shadow};
    animation: fadeInUp {delay:.2f}s ease both;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
">
    {poster_html}
    <div style="padding:16px">
        <div style="font-size:1.02rem;font-weight:800;color:#fff;margin-bottom:3px;
                    line-height:1.3" title="{movie.title}">
            {movie.title}
        </div>
        <div style="color:#6666aa;font-size:0.8rem;margin-bottom:8px">
            {movie.release_year} &middot; {stars} &middot; <span style="color:#777">{votes} votos</span>
        </div>
        <div style="margin-bottom:10px;line-height:1.9">{genre_tags}</div>
        <div style="color:#9999bb;font-size:0.82rem;line-height:1.6;margin-bottom:14px">
            {overview}
        </div>
        <a href="{movie.url}" target="_blank" style="
            display:inline-flex;align-items:center;gap:6px;
            background:linear-gradient(135deg,#E50914,#b20710);
            color:#fff;border-radius:8px;padding:8px 16px;
            font-size:0.8rem;font-weight:700;text-decoration:none;
            letter-spacing:0.4px;box-shadow:0 3px 12px #E5091440;
        ">
            Ver no TMDb &rarr;
        </a>
    </div>
</div>
"""
    st.markdown(card_html, unsafe_allow_html=True)


def render_results(movies: list[Movie], reply: str) -> None:
    st.markdown(NOW_SHOWING_HTML, unsafe_allow_html=True)
    st.markdown(
        f'<div style="color:#cccce8;font-size:0.97rem;margin-bottom:24px;'
        f'font-style:italic;border-left:3px solid #E50914;padding-left:14px">'
        f'{reply}</div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(3, gap="large")
    for i, (col, movie) in enumerate(zip(cols, movies)):
        with col:
            render_movie_card(movie, rank=i + 1)


def main() -> None:
    st.set_page_config(page_title="CineMatch", layout="wide")
    st.markdown(CINEMA_CSS, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown(
            '<div style="text-align:center;padding:12px 0 8px">'
            '<div style="font-size:1.35rem;font-weight:900;color:#E50914;letter-spacing:2px">CINEMATCH</div>'
            '<div style="color:#444466;font-size:0.73rem;margin-top:3px">Powered by TMDb</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.divider()
        if st.button("Nova busca", use_container_width=True):
            reset_flow()
            st.rerun()
        st.divider()
        st.markdown("**Como funciona:**")
        for n, step in [
            ("1.", "Responde 10 perguntas"),
            ("2.", "Analisamos genero, clima, epoca, referencias, ator e tema"),
            ("3.", "Mostramos os 3 filmes mais relevantes com poster e nota"),
        ]:
            st.markdown(f"{n} {step}")
        st.divider()
        st.caption("Dados: [The Movie Database](https://www.themoviedb.org/)")

    st.markdown(HEADER_HTML, unsafe_allow_html=True)
    st.markdown(GRADIENT_LINE_HTML, unsafe_allow_html=True)

    init_state()
    client = get_client()

    # Quando completo: mostra resultado no topo, conversa embaixo em expander
    if st.session_state.completed:
        render_results(st.session_state.movies, st.session_state.reply)
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("Ver conversa completa"):
            for message in st.session_state.messages:
                render_message(message)
        st.info("Quer tentar outra combinacao? Clique em **Nova busca** na barra lateral.")
        return

    # Barra de progresso
    step = st.session_state.step
    total = len(QUESTIONS)
    pct = step / total
    label = f"Pergunta {step + 1} de {total}" if step < total else "Processando..."
    st.progress(pct, text=f"**{label}** — {int(pct * 100)}% concluido")
    st.markdown("<br>", unsafe_allow_html=True)

    # Historico do chat
    for message in st.session_state.messages:
        render_message(message)

    # Input
    user_message = st.chat_input("Digite sua resposta...")
    if not user_message:
        return

    st.session_state.messages.append({"role": "user", "content": user_message})
    render_message(st.session_state.messages[-1])
    st.session_state.answers.append(user_message)
    st.session_state.step += 1

    if st.session_state.step < len(QUESTIONS):
        q, hint = QUESTIONS[st.session_state.step]
        next_msg = f"**{q}**\n\n*{hint}*"
        st.session_state.messages.append({"role": "assistant", "content": next_msg})
        render_message(st.session_state.messages[-1])
        st.rerun()
        return

    # Todas as 10 respostas coletadas
    with st.spinner("Analisando suas preferencias e buscando os filmes perfeitos..."):
        try:
            result = build_recommendation(st.session_state.answers, client)
        except MovieAPIError as exc:
            st.session_state.messages.append(
                {"role": "assistant", "content": f"Nao consegui buscar filmes: {exc}"}
            )
            render_message(st.session_state.messages[-1])
            return

    st.session_state.movies = result["movies"]
    st.session_state.reply = result["reply"]
    st.session_state.messages.append({"role": "assistant", "content": result["reply"]})
    st.session_state.completed = True
    st.rerun()


if __name__ == "__main__":
    main()
