from __future__ import annotations

import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterable

import requests

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_MOVIE_URL = "https://www.themoviedb.org/movie"
DEFAULT_LANGUAGE = "pt-BR"
GENRE_KEYWORDS = {
    "acao": "Action",
    "ação": "Action",
    "aventura": "Adventure",
    "animacao": "Animation",
    "animação": "Animation",
    "comedia": "Comedy",
    "comédia": "Comedy",
    "crime": "Crime",
    "documentario": "Documentary",
    "documentário": "Documentary",
    "drama": "Drama",
    "familia": "Family",
    "família": "Family",
    "fantasia": "Fantasy",
    "ficcao": "Science Fiction",
    "ficção": "Science Fiction",
    "ficção científica": "Science Fiction",
    "historico": "History",
    "histórico": "History",
    "terror": "Horror",
    "mistério": "Mystery",
    "misterio": "Mystery",
    "romance": "Romance",
    "ficção científica": "Science Fiction",
    "suspense": "Thriller",
    "thriller": "Thriller",
    "guerra": "War",
    "western": "Western",
}


@dataclass(frozen=True)
class Movie:
    id: int
    title: str
    release_date: str | None
    overview: str
    rating: float | None
    genres: list[str]
    poster_path: str | None

    @property
    def release_year(self) -> str:
        if not self.release_date:
            return "s/ data"
        return self.release_date[:4]

    @property
    def url(self) -> str:
        return f"{TMDB_MOVIE_URL}/{self.id}"


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
        query = {"api_key": self.api_key, "language": self.language}
        if params:
            query.update(params)
        response = self.session.get(f"{TMDB_BASE_URL}{path}", params=query, timeout=15)
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            raise MovieAPIError(f"Falha ao consultar a API de filmes: {exc}") from exc
        return response.json()

    @lru_cache(maxsize=1)
    def genres(self) -> dict[str, int]:
        payload = self._get("/genre/movie/list")
        return {item["name"]: item["id"] for item in payload.get("genres", [])}

    def discover_movies(
        self,
        genres: Iterable[str] | None = None,
        year: int | None = None,
        page: int = 1,
    ) -> list[Movie]:
        params: dict[str, Any] = {
            "sort_by": "popularity.desc",
            "page": page,
            "include_adult": False,
        }
        genre_ids = self._genre_ids(genres or [])
        if genre_ids:
            params["with_genres"] = ",".join(str(genre_id) for genre_id in genre_ids)
        if year:
            params["primary_release_year"] = year
        payload = self._get("/discover/movie", params=params)
        return self._parse_movies(payload.get("results", []))

    def search_movies(self, query: str, year: int | None = None) -> list[Movie]:
        params: dict[str, Any] = {"query": query, "include_adult": False}
        if year:
            params["year"] = year
        payload = self._get("/search/movie", params=params)
        return self._parse_movies(payload.get("results", []))

    def top_rated_movies(self) -> list[Movie]:
        payload = self._get("/movie/top_rated", params={"page": 1})
        return self._parse_movies(payload.get("results", []))

    def _genre_ids(self, names: Iterable[str]) -> list[int]:
        available = self.genres()
        ids: list[int] = []
        for name in names:
            genre_name = name.title()
            if genre_name in available:
                ids.append(available[genre_name])
        return ids

    def _parse_movies(self, items: Iterable[dict[str, Any]]) -> list[Movie]:
        movies: list[Movie] = []
        for item in items:
            if not item.get("title"):
                continue
            movies.append(
                Movie(
                    id=item["id"],
                    title=item["title"],
                    release_date=item.get("release_date") or None,
                    overview=item.get("overview") or "Sem sinopse disponível.",
                    rating=item.get("vote_average"),
                    genres=[],
                    poster_path=item.get("poster_path"),
                )
            )
        return movies[:5]


def extract_year(message: str) -> int | None:
    match = re.search(r"\b(19|20)\d{2}\b", message)
    if not match:
        return None
    return int(match.group(0))


def extract_genres(message: str) -> list[str]:
    text = message.lower()
    genres: list[str] = []
    for keyword, genre in GENRE_KEYWORDS.items():
        if keyword in text and genre not in genres:
            genres.append(genre)
    return genres


def normalize_message(message: str) -> str:
    return re.sub(r"\s+", " ", message.strip().lower())


def build_recommendation(message: str, client: TMDbClient, previous_filters: dict[str, Any] | None = None) -> dict[str, Any]:
    previous_filters = previous_filters or {}
    cleaned = normalize_message(message)
    year = extract_year(cleaned) or previous_filters.get("year")
    genres = extract_genres(cleaned) or previous_filters.get("genres", [])

    search_hint = cleaned
    search_triggered = False
    for prefix in ("quero ver ", "procure ", "buscar ", "me indique ", "recomende ", "sugira "):
        if search_hint.startswith(prefix):
            search_hint = search_hint[len(prefix):]
            search_triggered = True

    if genres or year:
        movies = client.discover_movies(genres=genres, year=year)
        focus = []
        if genres:
            focus.append(", ".join(genres))
        if year:
            focus.append(str(year))
        subtitle = " e ".join(focus)
        reply = f"Separei alguns filmes de {subtitle} para você."
    elif search_triggered or len(search_hint.split()) >= 2:
        movies = client.search_movies(search_hint)
        reply = f"Encontrei filmes parecidos com '{search_hint}'."
    else:
        movies = client.top_rated_movies()
        reply = "Posso indicar por gênero, ano ou título. Enquanto isso, deixei alguns filmes bem avaliados."

    if not movies:
        raise MovieAPIError("A API não retornou filmes para essa consulta.")

    next_filters = {"year": year, "genres": genres}
    return {"reply": reply, "movies": movies, "filters": next_filters}


def format_movies(movies: list[Movie]) -> str:
    lines = []
    for movie in movies:
        rating = f"{movie.rating:.1f}" if movie.rating is not None else "N/A"
        lines.append(
            f"- **{movie.title}** ({movie.release_year}) — nota {rating}\n  {movie.overview}\n  [Abrir no TMDb]({movie.url})"
        )
    return "\n".join(lines)


def load_tmdb_api_key() -> str:
    return os.getenv("TMDB_API_KEY", "").strip()
