from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Iterable

import requests

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_MOVIE_URL = "https://www.themoviedb.org/movie"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"
DEFAULT_LANGUAGE = "pt-BR"

MIN_VOTE_COUNT = 300
MIN_RATING = 6.0
TOP_N_MOVIES = 3
BAYESIAN_PRIOR_VOTES = 300
BAYESIAN_MEAN_RATING = 6.5

GENRE_KEYWORDS: dict[str, str] = {
    "acao": "Action", "ação": "Action",
    "aventura": "Adventure",
    "animacao": "Animation", "animação": "Animation", "anime": "Animation",
    "comedia": "Comedy", "comédia": "Comedy", "comédia": "Comedy",
    "crime": "Crime",
    "documentario": "Documentary", "documentário": "Documentary",
    "drama": "Drama",
    "familia": "Family", "família": "Family",
    "fantasia": "Fantasy",
    "ficcao": "Science Fiction", "ficção": "Science Fiction",
    "ficção científica": "Science Fiction", "sci-fi": "Science Fiction",
    "historico": "History", "histórico": "History",
    "terror": "Horror", "horror": "Horror",
    "mistério": "Mystery", "misterio": "Mystery",
    "romance": "Romance",
    "suspense": "Thriller", "thriller": "Thriller",
    "guerra": "War",
    "western": "Western",
    "musical": "Music", "música": "Music", "music": "Music",
}

MOOD_GENRE_MAP: dict[str, list[str]] = {
    "leve": ["Comedy", "Family", "Animation"],
    "levinho": ["Comedy", "Family"],
    "engraçado": ["Comedy"], "engracado": ["Comedy"],
    "divertido": ["Comedy", "Adventure"],
    "emocionante": ["Action", "Adventure", "Drama"],
    "intenso": ["Thriller", "Drama", "Crime"],
    "pesado": ["Drama", "Crime"],
    "triste": ["Drama"],
    "chorar": ["Drama", "Romance"],
    "romantico": ["Romance", "Drama"], "romântico": ["Romance"],
    "assustador": ["Horror"],
    "misterioso": ["Mystery", "Thriller"],
    "reflexivo": ["Drama", "Documentary"],
    "inspirador": ["Drama", "History"],
    "animado": ["Animation", "Comedy"],
    "épico": ["Action", "Adventure", "History"], "epico": ["Action", "Adventure"],
    "sombrio": ["Horror", "Thriller", "Crime"],
    "curioso": ["Documentary", "Mystery"],
    "gargalhar": ["Comedy"],
    "agitado": ["Action", "Adventure"],
    "tenso": ["Thriller", "Horror"],
    "emocionado": ["Drama", "Romance"],
    "empolgado": ["Action", "Adventure"],
}

CONTEXT_MAP: dict[str, list[str]] = {
    "casal": ["Romance", "Drama"],
    "namoro": ["Romance", "Drama"], "namorado": ["Romance", "Drama"], "namorada": ["Romance", "Drama"],
    "noivo": ["Romance", "Drama"], "noiva": ["Romance", "Drama"],
    "família": ["Family", "Animation", "Comedy"], "familia": ["Family", "Animation", "Comedy"],
    "criança": ["Family", "Animation"], "crianca": ["Family", "Animation"],
    "filho": ["Family", "Animation"], "filhos": ["Family", "Animation"],
    "kid": ["Family", "Animation"], "kids": ["Family", "Animation"],
    "amigo": ["Comedy", "Action"], "amigos": ["Comedy", "Action"],
    "galera": ["Comedy", "Action"],
    "grupo": ["Comedy", "Action"],
}

LANGUAGE_MAP: dict[str, str] = {
    "brasil": "pt", "brasileiro": "pt", "nacional": "pt",
    "português": "pt", "portugues": "pt",
    "americano": "en", "inglês": "en", "ingles": "en", "hollywood": "en",
    "frances": "fr", "francês": "fr", "france": "fr",
    "espanhol": "es", "español": "es",
    "italiano": "it",
    "alemão": "de", "alemao": "de",
    "japones": "ja", "japonês": "ja", "japão": "ja",
    "coreano": "ko", "korea": "ko",
    "chinês": "zh", "chines": "zh",
    "hindi": "hi", "india": "hi",
}

RUNTIME_PATTERNS: list[tuple[str, tuple[int | None, int | None]]] = [
    (r"curto|curta|r[áa]pido|1h30|90\s*min|\bshort\b", (None, 100)),
    (r"longo|longa|[eé]pico|epico|2h|2\s*hora|\blong\b", (120, None)),
]

THEME_MAP: dict[str, str] = {

    "luta": "Action", "briga": "Action", "tiro": "Action", "policial": "Crime",
    "perseguição": "Action", "perseguicao": "Action", "explosão": "Action", "explosao": "Action",
    "superpoder": "Action", "super heroi": "Action", "super-heroi": "Action", "superhero": "Action",


    "corrida": "Action", "corridas": "Action", "carro": "Action", "carros": "Action",
    "automobilismo": "Action", "formula 1": "Action", "fórmula 1": "Action",
    "racing": "Action", "race": "Action", "moto": "Action", "motos": "Action",
    "esporte": "Drama", "sport": "Drama", "futebol": "Drama", "basquete": "Drama",
    "boxe": "Drama", "luta livre": "Drama",


    "heist": "Crime", "assalto": "Crime", "roubo": "Crime", "máfia": "Crime", "mafia": "Crime",
    "gangster": "Crime", "trafico": "Crime", "tráfico": "Crime", "policia": "Crime", "polícia": "Crime",
    "detetive": "Mystery", "detective": "Mystery", "investigação": "Mystery", "investigacao": "Mystery",
    "mistério": "Mystery", "misterio": "Mystery",


    "vingança": "Thriller", "vinganca": "Thriller", "revenge": "Thriller",
    "survival": "Thriller", "sobrevivência": "Thriller", "sobrevivencia": "Thriller",
    "espionagem": "Thriller", "espio": "Thriller", "spy": "Thriller",
    "serial killer": "Thriller", "sequestro": "Thriller", "psicopata": "Thriller",
    "zumbi": "Horror", "zombie": "Horror", "fantasma": "Horror", "demônio": "Horror", "demonio": "Horror",
    "assombração": "Horror", "assombracao": "Horror",


    "viagem no tempo": "Science Fiction", "time travel": "Science Fiction",
    "espaço": "Science Fiction", "espaco": "Science Fiction", "space": "Science Fiction",
    "apocalipse": "Science Fiction", "apocalypse": "Science Fiction",
    "robô": "Science Fiction", "robo": "Science Fiction", "robôs": "Science Fiction", "robos": "Science Fiction",
    "alien": "Science Fiction", "aliens": "Science Fiction", "inteligência artificial": "Science Fiction",
    "inteligencia artificial": "Science Fiction", "magia": "Fantasy", "dragão": "Fantasy", "dragao": "Fantasy",


    "amizade": "Drama", "friendship": "Drama", "redenção": "Drama", "redencao": "Drama", "redemption": "Drama",
    "superação": "Drama", "superacao": "Drama", "familia": "Drama", "família": "Drama",
    "amor": "Romance", "paixão": "Romance", "paixao": "Romance",
    "dança": "Music", "danca": "Music", "dance": "Music", "música": "Music", "musica": "Music", "banda": "Music",


    "guerra": "War", "batalha": "War", "soldado": "War",
    "velho oeste": "Western", "faroeste": "Western", "cowboy": "Western",
}


THEME_TO_KEYWORD: dict[str, str] = {

    "luta": "fight", "briga": "fight", "tiro": "shootout", "policial": "police",
    "perseguição": "chase", "perseguicao": "chase", "explosão": "explosion", "explosao": "explosion",
    "super heroi": "superhero", "super-heroi": "superhero", "superhero": "superhero",


    "corrida": "car race", "corridas": "car race", "carro": "car race", "carros": "car race",
    "automobilismo": "auto racing", "formula 1": "formula one", "fórmula 1": "formula one",
    "racing": "car race", "race": "car race", "moto": "motorcycle", "motos": "motorcycle",
    "esporte": "sport", "sport": "sport", "futebol": "football", "basquete": "basketball",
    "boxe": "boxing", "luta livre": "wrestling",


    "heist": "heist", "assalto": "heist", "roubo": "heist",
    "máfia": "mafia", "mafia": "mafia", "gangster": "gangster",
    "trafico": "drug trafficking", "tráfico": "drug trafficking",
    "policia": "police", "polícia": "police",
    "detetive": "detective", "detective": "detective",
    "investigação": "detective", "investigacao": "detective",


    "vingança": "revenge", "vinganca": "revenge", "revenge": "revenge",
    "espionagem": "spy", "espio": "spy", "spy": "spy",
    "zumbi": "zombie", "zombie": "zombie",
    "serial killer": "serial killer", "assassino serial": "serial killer",
    "sobrevivência": "survival", "sobrevivencia": "survival", "survival": "survival",
    "apocalipse": "post-apocalyptic", "apocalypse": "post-apocalyptic",
    "sequestro": "kidnapping", "psicopata": "psychopath",
    "fantasma": "ghost", "demônio": "demon", "demonio": "demon",


    "viagem no tempo": "time travel", "time travel": "time travel",
    "espaço": "space", "espaco": "space", "space": "space",
    "robô": "robot", "robo": "robot", "robôs": "robot", "robos": "robot",
    "alien": "alien", "aliens": "alien",
    "inteligência artificial": "artificial intelligence", "inteligencia artificial": "artificial intelligence",
    "magia": "magic", "dragão": "dragon", "dragao": "dragon",


    "amizade": "friendship", "friendship": "friendship",
    "redenção": "redemption", "redencao": "redemption", "redemption": "redemption",
    "superação": "based on true story", "superacao": "based on true story",
    "amor": "love", "paixão": "love", "paixao": "love",
    "dança": "dance", "danca": "dance", "dance": "dance",
    "música": "music", "musica": "music", "banda": "music",


    "guerra": "war", "batalha": "battle", "soldado": "soldier",
    "velho oeste": "western", "faroeste": "western", "cowboy": "cowboy",
}


GENRE_IDS: dict[str, int] = {
    "Action": 28, "Adventure": 12, "Animation": 16, "Comedy": 35,
    "Crime": 80, "Documentary": 99, "Drama": 18, "Family": 10751,
    "Fantasy": 14, "History": 36, "Horror": 27, "Music": 10402,
    "Mystery": 9648, "Romance": 10749, "Science Fiction": 878,
    "Thriller": 53, "War": 10752, "Western": 37,
}
GENRE_ID_TO_NAME: dict[int, str] = {v: k for k, v in GENRE_IDS.items()}

NEGATIVE_REFERENCE = {
    "não", "nao", "nenhum", "nada", "sem referência", "sem referencia",
    "não tenho", "nao tenho", "nenhuma", "tanto faz", "qualquer", "sem",
    "nope", "n", "não sei", "nao sei", "nunca vi", "nenhum filme",
}


@dataclass(frozen=True)
class Movie:
    id: int
    title: str
    release_date: str | None
    overview: str
    rating: float | None
    genres: list[str] = field(default_factory=list)
    poster_path: str | None = None
    genre_ids: list[int] = field(default_factory=list)
    original_language: str | None = None
    original_title: str | None = None
    popularity: float | None = None
    vote_count: int | None = None
    imdb_id: str | None = None
    runtime: int | None = None

    @property
    def release_year(self) -> str:
        return self.release_date[:4] if self.release_date else "s/d"

    @property
    def url(self) -> str:
        return f"{TMDB_MOVIE_URL}/{self.id}"

    def poster_url(self, size: str = "w500") -> str | None:
        return f"{TMDB_IMAGE_BASE}/{size}{self.poster_path}" if self.poster_path else None

    def score(self) -> float:
        rating = self.rating or 0.0
        votes = self.vote_count or 0
        if votes == 0:
            return 0.0
        m = BAYESIAN_PRIOR_VOTES
        C = BAYESIAN_MEAN_RATING
        return (votes / (votes + m)) * rating + (m / (votes + m)) * C


class MovieAPIError(RuntimeError):
    pass


class TMDbClient:
    def __init__(self, api_key: str, language: str = DEFAULT_LANGUAGE) -> None:
        api_key = api_key.strip()
        if not api_key:
            raise MovieAPIError("A chave TMDB_API_KEY não foi configurada.")
        self.api_key = api_key
        self.language = language
        self.session = requests.Session()

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        query: dict[str, Any] = {"api_key": self.api_key, "language": self.language}
        if params:
            query.update(params)
        resp = self.session.get(f"{TMDB_BASE_URL}{path}", params=query, timeout=15)
        try:
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise MovieAPIError(f"Falha na API de filmes: {exc}") from exc
        return resp.json()

    @lru_cache(maxsize=1)
    def genres(self) -> dict[str, int]:
        payload = self._get("/genre/movie/list")
        return {item["name"]: item["id"] for item in payload.get("genres", [])}

    def discover_movies(
        self,
        genres: Iterable[str] | None = None,
        year: int | None = None,
        year_gte: int | None = None,
        year_lte: int | None = None,
        language: str | None = None,
        runtime_gte: int | None = None,
        runtime_lte: int | None = None,
        sort_by: str = "vote_count.desc",
        keyword_id: int | None = None,
        pages: int = 2,
    ) -> list[Movie]:
        base_params: dict[str, Any] = {
            "sort_by": sort_by,
            "include_adult": False,
            "vote_count.gte": MIN_VOTE_COUNT,
            "vote_average.gte": MIN_RATING,
        }
        genre_ids = self._genre_ids(genres or [])
        if genre_ids:
            base_params["with_genres"] = ",".join(str(gid) for gid in genre_ids)
        if year:
            base_params["primary_release_year"] = year
        if year_gte:
            base_params["primary_release_date.gte"] = f"{year_gte}-01-01"
        if year_lte:
            base_params["primary_release_date.lte"] = f"{year_lte}-12-31"
        if language:
            base_params["with_original_language"] = language
        if runtime_gte is not None:
            base_params["with_runtime.gte"] = runtime_gte
        if runtime_lte is not None:
            base_params["with_runtime.lte"] = runtime_lte
        if keyword_id is not None:
            base_params["with_keywords"] = str(keyword_id)

        movies: list[Movie] = []
        seen: set[int] = set()
        for page in range(1, pages + 1):
            payload = self._get("/discover/movie", params={**base_params, "page": page})
            for m in self._parse_movies(payload.get("results", [])):
                if m.id not in seen:
                    seen.add(m.id)
                    movies.append(m)
        return movies

    def search_movies(self, query: str, year: int | None = None) -> list[Movie]:
        params: dict[str, Any] = {"query": query, "include_adult": False}
        if year:
            params["year"] = year
        payload = self._get("/search/movie", params=params)
        return self._parse_movies(payload.get("results", []))

    def top_rated_movies(self) -> list[Movie]:
        payload = self._get("/movie/top_rated", params={"page": 1})
        return self._parse_movies(payload.get("results", []))

    def movie_recommendations(self, movie_id: int) -> list[Movie]:

        pool: list[Movie] = []
        seen: set[int] = set()
        for endpoint in (f"/movie/{movie_id}/recommendations", f"/movie/{movie_id}/similar"):
            try:
                payload = self._get(endpoint)
                for m in self._parse_movies(payload.get("results", [])):
                    if m.id not in seen:
                        seen.add(m.id)
                        pool.append(m)
            except MovieAPIError:
                pass
        return pool

    def search_keyword_id(self, term: str) -> int | None:

        try:
            payload = self._get("/search/keyword", {"query": term})
            results = payload.get("results", [])
            return results[0]["id"] if results else None
        except MovieAPIError:
            return None

    def person_movies(self, name: str) -> list[Movie]:
        try:
            payload = self._get("/search/person", {"query": name})
            results = payload.get("results", [])
            if not results:
                return []
            person_id = results[0]["id"]
            credits = self._get(f"/person/{person_id}/movie_credits")
            cast = credits.get("cast", [])
            directed = [m for m in credits.get("crew", []) if m.get("job") == "Director"]
            combined = {m["id"]: m for m in cast + directed}.values()
            sorted_movies = sorted(combined, key=lambda x: x.get("popularity", 0), reverse=True)
            return self._parse_movies(list(sorted_movies)[:25])
        except MovieAPIError:
            return []

    def _genre_ids(self, names: Iterable[str]) -> list[int]:

        return [GENRE_IDS[n] for n in names if n in GENRE_IDS]

    def _parse_movies(self, items: Iterable[dict[str, Any]]) -> list[Movie]:


        movies: list[Movie] = []
        for item in items:
            if not item.get("title"):
                continue

            raw_genres = item.get("genres", [])
            if raw_genres:
                genres: list[str] = [GENRE_ID_TO_NAME[g["id"]] for g in raw_genres if g.get("id") in GENRE_ID_TO_NAME]
            else:

                genres = [GENRE_ID_TO_NAME[gid] for gid in (item.get("genre_ids") or []) if gid in GENRE_ID_TO_NAME]
            movies.append(Movie(
                id=item["id"],
                title=item["title"],
                release_date=item.get("release_date") or None,
                overview=item.get("overview") or "Sem sinopse disponivel.",
                rating=item.get("vote_average"),
                genres=genres,
                poster_path=item.get("poster_path"),
                genre_ids=item.get("genre_ids") or [],
                original_language=item.get("original_language"),
                original_title=item.get("original_title"),
                popularity=item.get("popularity"),
                vote_count=item.get("vote_count"),
            ))
        return movies


def remove_accents(text: str) -> str:

    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", remove_accents(text).strip().lower())


def extract_year(text: str) -> int | None:
    m = re.search(r"\b(19|20)\d{2}\b", text)
    return int(m.group(0)) if m else None


def extract_decade(text: str) -> tuple[int, int] | None:
    patterns = [
        (r"anos?\s*60|d[eé]cada\s*de\s*60", (1960, 1969)),
        (r"anos?\s*70|d[eé]cada\s*de\s*70", (1970, 1979)),
        (r"anos?\s*80|d[eé]cada\s*de\s*80|80s", (1980, 1989)),
        (r"anos?\s*90|d[eé]cada\s*de\s*90|90s", (1990, 1999)),
        (r"anos?\s*2000|d[eé]cada\s*de\s*2000|2000s", (2000, 2009)),
        (r"anos?\s*2010|d[eé]cada\s*de\s*2010|2010s", (2010, 2019)),
        (r"anos?\s*2020|recente|moderno|atual|novo|lan[cç]amento", (2020, 2026)),
        (r"cl[aá]ssico|antigo|vintage|old", (1950, 1989)),
    ]
    t = normalize(text)
    for pattern, year_range in patterns:
        if re.search(pattern, t):
            return year_range
    return None


def extract_genres(text: str) -> list[str]:
    t = normalize(text)
    genres: list[str] = []
    for kw, genre in GENRE_KEYWORDS.items():
        if kw in t and genre not in genres:
            genres.append(genre)
    return genres


def extract_mood_genres(text: str) -> list[str]:
    t = normalize(text)
    genres: list[str] = []
    for kw, genre_list in MOOD_GENRE_MAP.items():
        if kw in t:
            for g in genre_list:
                if g not in genres:
                    genres.append(g)
    return genres


def extract_context_genres(text: str) -> list[str]:
    t = normalize(text)
    genres: list[str] = []
    for kw, genre_list in CONTEXT_MAP.items():
        if kw in t:
            for g in genre_list:
                if g not in genres:
                    genres.append(g)
    return genres


def extract_theme_genres(text: str) -> list[str]:
    t = normalize(text)
    genres: list[str] = []
    for kw, genre in THEME_MAP.items():
        if kw in t and genre not in genres:
            genres.append(genre)
    return genres + [g for g in extract_genres(text) if g not in genres]


def extract_language(text: str) -> str | None:
    t = normalize(text)
    for kw, code in LANGUAGE_MAP.items():
        if kw in t:
            return code
    return None


def extract_runtime(text: str) -> tuple[int | None, int | None]:
    t = normalize(text)
    for pattern, (gte, lte) in RUNTIME_PATTERNS:
        if re.search(pattern, t):
            return (gte, lte)
    return (None, None)


def extract_sort_order(text: str) -> str:
    t = text.lower()
    if any(kw in t for kw in ("público", "publico", "popular", "bilheteria", "blockbuster", "mais visto")):
        return "popularity.desc"
    if any(kw in t for kw in ("critica", "crítica", "oscar", "cannes", "festival", "premiado")):
        return "vote_average.desc"

    return "vote_count.desc"


def is_negative(text: str) -> bool:
    t = normalize(text)
    negative = {normalize(item) for item in NEGATIVE_REFERENCE}
    return t in negative or len(t) <= 2


def preference_score(
    movie: Movie,
    user_genres: list[str],
    year_gte: int | None,
    year_lte: int | None,
    language: str | None = None,
) -> float:

    base = movie.score()

    if user_genres and movie.genres:
        movie_genre_set = set(movie.genres)
        matches = sum(1 for g in user_genres if g in movie_genre_set)
        base += (matches / len(user_genres)) * 3.0

    if movie.release_date and (year_gte or year_lte):
        try:
            y = int(movie.release_date[:4])
            if (year_gte is None or y >= year_gte) and (year_lte is None or y <= year_lte):
                base += 0.8
        except (ValueError, TypeError):
            pass

    if language and movie.original_language == language:
        base += 0.4

    return base


def rank_movies(
    movies: list[Movie],
    user_genres: list[str] | None = None,
    year_gte: int | None = None,
    year_lte: int | None = None,
    language: str | None = None,
    limit: int = TOP_N_MOVIES,
) -> list[Movie]:

    required_genres = set(user_genres or [])

    best_pool: list[Movie] = []
    for min_votes, min_rating in ((MIN_VOTE_COUNT, MIN_RATING), (200, 6.0), (50, 5.0), (0, 0.0)):
        filtered = [
            m for m in movies
            if (m.vote_count or 0) >= min_votes and (m.rating or 0) >= min_rating
        ]

        if required_genres:
            genre_filtered = [
                m for m in filtered
                if set(m.genres).intersection(required_genres)
            ]


            if len(genre_filtered) >= limit:
                best_pool = genre_filtered
                break
            if genre_filtered and not best_pool:
                best_pool = genre_filtered

        if len(filtered) >= limit and not required_genres:
            best_pool = filtered
            break

        if filtered and not best_pool:
            best_pool = filtered

    pool = best_pool if best_pool else movies

    return sorted(
        pool,
        key=lambda m: preference_score(m, user_genres or [], year_gte, year_lte, language),
        reverse=True,
    )[:limit]

def _cascading_discover(
    client: TMDbClient,
    genres: list[str],
    year: int | None,
    year_gte: int | None,
    year_lte: int | None,
    keyword_id: int | None,
    sort_by: str,
    target: int = 15,
) -> list[Movie]:


    steps: list[dict[str, Any]] = []


    if genres and (year or year_gte) and keyword_id:
        steps.append(dict(genres=genres, year=year, year_gte=year_gte, year_lte=year_lte, keyword_id=keyword_id))
    if genres and keyword_id:
        steps.append(dict(genres=genres, keyword_id=keyword_id))
    if (year or year_gte) and keyword_id:
        steps.append(dict(year=year, year_gte=year_gte, year_lte=year_lte, keyword_id=keyword_id))
    if keyword_id:
        steps.append(dict(keyword_id=keyword_id))
    if genres and (year or year_gte):
        steps.append(dict(genres=genres, year=year, year_gte=year_gte, year_lte=year_lte))
    if genres:
        steps.append(dict(genres=genres))
    if year or year_gte:
        steps.append(dict(year=year, year_gte=year_gte, year_lte=year_lte))

    pool: list[Movie] = []
    seen: set[int] = set()

    for step in steps:
        results = client.discover_movies(**step, sort_by=sort_by, pages=2)
        for m in results:
            if m.id not in seen:
                seen.add(m.id)
                pool.append(m)
        quality = [m for m in pool if (m.vote_count or 0) >= 300 and (m.rating or 0) >= 6.5]
        if len(quality) >= target:
            break

    return pool


def build_recommendation(answers: list[str], client: TMDbClient) -> dict[str, Any]:
    def ans(i: int) -> str:
        return normalize(answers[i]) if i < len(answers) else ""

    genre_ans   = ans(0)
    mood_ans    = ans(1)
    context_ans = ans(2)
    time_ans    = ans(3)
    lang_ans    = ans(4)
    runtime_ans = ans(5)
    acclaim_ans = ans(6)
    ref_ans     = ans(7)
    person_ans  = ans(8)
    theme_ans   = ans(9)


    primary_genres = extract_genres(genre_ans)


    theme_genres = extract_theme_genres(theme_ans)


    hard_genres = list(dict.fromkeys(primary_genres + theme_genres))


    scoring_genres = list(dict.fromkeys(
        hard_genres
        + extract_mood_genres(mood_ans)
        + extract_context_genres(context_ans)
    ))


    decade = extract_decade(time_ans)
    if decade:
        year = None
        year_gte, year_lte = decade
    else:
        year = extract_year(time_ans)
        year_gte = year_lte = None

    language = extract_language(lang_ans)
    sort_by = extract_sort_order(acclaim_ans)


    keyword_id: int | None = None
    if theme_ans and not is_negative(theme_ans):
        for kw, tmdb_term in THEME_TO_KEYWORD.items():
            if kw in theme_ans:
                keyword_id = client.search_keyword_id(tmdb_term)
                break


        if keyword_id is None:
            keyword_id = client.search_keyword_id(theme_ans)

    movie_pool: list[Movie] = []
    ref_movie_title: str | None = None
    person_name: str | None = None


    if ref_ans and not is_negative(ref_ans):
        ref_results = client.search_movies(ref_ans)
        if ref_results:
            ref_movie_title = ref_results[0].title
            movie_pool.extend(client.movie_recommendations(ref_results[0].id))


    if person_ans and not is_negative(person_ans):
        person_name = person_ans.title()
        existing = {m.id for m in movie_pool}
        movie_pool.extend(m for m in client.person_movies(person_ans) if m.id not in existing)


    if hard_genres or year or year_gte or keyword_id:
        discovered = _cascading_discover(
            client, hard_genres, year, year_gte, year_lte, keyword_id, sort_by
        )
        existing = {m.id for m in movie_pool}
        movie_pool.extend(m for m in discovered if m.id not in existing)


    if not movie_pool:
        movie_pool = client.top_rated_movies()

    if not movie_pool:
        raise MovieAPIError("A API nao retornou filmes para essa consulta.")

    ranked = rank_movies(
        movie_pool,
        user_genres=scoring_genres,
        year_gte=year_gte,
        year_lte=year_lte,
        language=language,
    )


    if decade:
        decade_label = f"anos {decade[0]}" if decade[0] >= 2000 else f"anos {str(decade[0])[2:]}"
    else:
        decade_label = ""

    parts: list[str] = []
    if scoring_genres:
        parts.append(", ".join(scoring_genres[:3]))
    if year:
        parts.append(str(year))
    elif decade:
        parts.append(decade_label)

    if ref_movie_title and person_name:
        reply = f"Cruzei recomendações de **{ref_movie_title}** com filmes de **{person_name}**"
        if parts:
            reply += f" ({', '.join(parts)})"
        reply += ". Aqui estão os 3 melhores para você:"
    elif ref_movie_title:
        reply = f"Baseado em **{ref_movie_title}**"
        if parts:
            reply += f", filtrei os melhores filmes de {' e '.join(parts)}"
        reply += ". Aqui estão os 3 filmes perfeitos para você:"
    elif person_name:
        reply = f"Selecionei os melhores trabalhos de **{person_name}**"
        if parts:
            reply += f" no estilo {', '.join(parts)}"
        reply += ":"
    elif parts:
        reply = f"Encontrei os **3 melhores filmes** de {' e '.join(parts)} para você:"
    else:
        reply = "Baseado no seu perfil, aqui estão os **3 filmes mais bem avaliados** para você:"

    return {"reply": reply, "movies": ranked}


def load_tmdb_api_key() -> str:
    return os.getenv("TMDB_API_KEY", "").strip()
