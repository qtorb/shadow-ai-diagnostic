"""Cliente simple para Google Books API."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

GOOGLE_BOOKS_ENDPOINT = "https://www.googleapis.com/books/v1/volumes"


def _looks_fiction(categories: list[str]) -> bool:
    joined = " ".join(categories).lower()
    return "fiction" in joined and "nonfiction" not in joined


def search_google_books(
    query: str,
    language: str = "",
    max_results: int = 5,
    non_fiction_only: bool = False,
) -> tuple[list[dict[str, Any]], str | None]:
    """Devuelve libros normalizados y error opcional."""
    params = {
        "q": query,
        "maxResults": max(1, min(20, max_results)),
        "orderBy": "newest",
        "printType": "books",
    }
    if language:
        params["langRestrict"] = language.lower()

    url = f"{GOOGLE_BOOKS_ENDPOINT}?{urlencode(params)}"

    try:
        with urlopen(url, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [], f"Google Books no disponible: {exc}"

    books: list[dict[str, Any]] = []
    for item in payload.get("items", []):
        info = item.get("volumeInfo", {})
        title = (info.get("title") or "").strip()
        authors = info.get("authors") or []
        author = ", ".join(authors).strip()
        categories = info.get("categories") or []

        if not title:
            continue
        if non_fiction_only and _looks_fiction(categories):
            continue

        books.append(
            {
                "titulo": title,
                "autor": author,
                "editorial": (info.get("publisher") or "").strip(),
                "fecha_publicacion": (info.get("publishedDate") or "").strip(),
                "idioma": (info.get("language") or "").strip(),
                "descripcion": (info.get("description") or "").strip(),
                "source_url": (info.get("infoLink") or "").strip(),
                "fuente_origen": "google_books",
                "raw_categories": categories,
            }
        )

    return books, None
