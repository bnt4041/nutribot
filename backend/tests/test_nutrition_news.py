"""Tests for the nutrition news headline fetcher (used by the 'news' reminder type)."""

from app.services import nutrition_news

SAMPLE_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Google News</title>
    <item>
      <title>Comer m\xc3\xa1s fibra reduce el riesgo cardiovascular - Diario Salud</title>
      <link>https://example.com/fibra</link>
      <source url="https://example.com">Diario Salud</source>
    </item>
    <item>
      <title>Sin enlace</title>
      <source>Fuente</source>
    </item>
  </channel>
</rss>
"""


def test_parse_items_extracts_title_link_source():
    items = nutrition_news.parse_items(SAMPLE_RSS)
    assert len(items) == 1
    assert items[0]["link"] == "https://example.com/fibra"
    assert items[0]["source"] == "Diario Salud"
    assert "fibra" in items[0]["title"]


def test_parse_items_skips_entries_without_link():
    items = nutrition_news.parse_items(SAMPLE_RSS)
    assert all(item["link"] for item in items)


def test_parse_items_empty_feed():
    empty = b"<rss version='2.0'><channel></channel></rss>"
    assert nutrition_news.parse_items(empty) == []


def test_format_message_with_headline():
    headline = {"title": "Titulo", "link": "https://example.com/x", "source": "Fuente"}
    text = nutrition_news.format_message(headline)
    assert text.startswith("📰 Titulo (Fuente)")
    assert "https://example.com/x" in text


def test_format_message_without_headline_uses_fallback():
    assert nutrition_news.format_message(None) == nutrition_news.FALLBACK_MESSAGE
