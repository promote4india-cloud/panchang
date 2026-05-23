"""Scraper package — fetcher, registry, parsers."""

from .fetcher import fetch_page, get_cached_page
from .registry import (
    ParsedFestival,
    ParsedMuhurat,
    ParserFn,
    get_parser,
    register_parser,
)

__all__ = [
    "fetch_page",
    "get_cached_page",
    "ParsedFestival",
    "ParsedMuhurat",
    "ParserFn",
    "get_parser",
    "register_parser",
]
