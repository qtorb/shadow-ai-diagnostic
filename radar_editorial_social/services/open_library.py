"""Cliente simple para Open Library Search API."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

OPEN_LIBRARY_ENDPOINT = "https://openlibrary.org/search.json"


def _matches_language(doc: dict[str, Any], language: str) -> bool:
    if not language:
        return True
    langs = doc.get("language") or []
    return language.lower() in [str(item).lower() for item in langs]


def _looks_fiction(subjects: list[str]) -> bool:
    joined = " ".join(subjects).lower()
    return "fiction" in joined and "non fiction" not in joined and "nonfiction" not in joined


def search_open_library(
    query: str,
    language: str = "",
    max_results: int = 5,
    non_fiction_only: bool = False,
) -> tuple[list[dict[str, Any]], str | None]:
    """Devuelve libros normalizados y error opcional."""
    params = {"q": query, "limit": max(1, min(20, max_results)), "sort": "new"}
    url = f"{OPEN_LIBRARY_ENDPOINT}?{urlencode(params)}"

    try:
        with urlopen(url, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return [], f"Open Library no disponible: {exc}"

    books: list[dict[str, Any]] = []
    for doc in payload.get("docs", []):
        title = (doc.get("title") or "").strip()
        if not title:
            continue
        if not _matches_language(doc, language):
            continue

        subjects = doc.get("subject") or []
        if non_fiction_only and _looks_fiction(subjects):
            continue

        author_names = doc.get("author_name") or []
        first_publish_year = doc.get("first_publish_year")
        edition_keys = doc.get("edition_key") or []
        source_url = f"https://openlibrary.org/books/{edition_keys[0]}" if edition_keys else ""

        books.append(
            {
                "titulo": title,
                "autor": ", ".join(author_names).strip(),
                "editorial": "",
                "fecha_publicacion": str(first_publish_year) if first_publish_year else "",
                "idioma": language.lower() if language else "",
                "descripcion": "",
                "source_url": source_url,
                "fuente_origen": "open_library",
                "raw_categories": subjects,
            }
        )

    return books, None
