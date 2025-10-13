"""Helpers to sanitize user-generated HTML content before persisting it."""

from __future__ import annotations

import bleach

_ALLOWED_TAGS: tuple[str, ...] = (
    "a",
    "abbr",
    "b",
    "blockquote",
    "br",
    "code",
    "em",
    "i",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "u",
    "ul",
)

_ALLOWED_ATTRIBUTES: dict[str, set[str]] = {
    "a": {"href", "title", "rel"},
}

_ALLOWED_PROTOCOLS: tuple[str, ...] = ("http", "https", "mailto")


def sanitize_user_html(raw: str) -> str:
    """Sanitize forum and form content to mitigate stored XSS risks."""

    cleaned = bleach.clean(
        raw or "",
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRIBUTES,
        protocols=_ALLOWED_PROTOCOLS,
        strip=True,
    )
    # bleach escapes HTML entities by default; ensure consistent whitespace
    return cleaned.strip()
