"""Fetches a nutrition/health news headline for the optional "news" reminder
type. Uses Google News RSS: a public feed that needs no API key/signup and
supports free-text queries + language/country targeting.
"""

import random
from xml.etree import ElementTree

import httpx

RSS_URL = "https://news.google.com/rss/search"
DEFAULT_QUERY = "nutrición OR alimentación saludable OR dieta saludable"
FALLBACK_MESSAGE = "📰 Hoy no he encontrado noticias de nutrición, pero sigue cuidándote."

# Only pick among the freshest results; Google News sorts by relevance/recency.
_CANDIDATE_POOL = 10


def parse_items(xml_bytes: bytes) -> list[dict]:
    """Parse a Google News RSS feed into a list of {title, link, source} dicts."""
    root = ElementTree.fromstring(xml_bytes)
    items = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        source = (item.findtext("source") or "").strip()
        if title and link:
            items.append({"title": title, "link": link, "source": source})
    return items


async def fetch_headline(
    query: str = DEFAULT_QUERY, lang: str = "es", country: str = "ES"
) -> dict | None:
    """Fetch one random recent headline. Returns None if the feed is empty."""
    params = {"q": query, "hl": lang, "gl": country, "ceid": f"{country}:{lang}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(RSS_URL, params=params)
        response.raise_for_status()
    items = parse_items(response.content)
    if not items:
        return None
    return random.choice(items[:_CANDIDATE_POOL])


def format_message(headline: dict | None) -> str:
    if headline is None:
        return FALLBACK_MESSAGE
    text = f"📰 {headline['title']}"
    if headline.get("source"):
        text += f" ({headline['source']})"
    if headline.get("link"):
        text += f"\n{headline['link']}"
    return text
