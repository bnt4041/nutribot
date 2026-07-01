"""Tests for the Telegram reply sanitizer."""

from app.services.deepseek.format import sanitize_for_telegram


def test_strips_bold_markers():
    assert sanitize_for_telegram("Tiene **42 kcal** por 100 ml") == (
        "Tiene 42 kcal por 100 ml"
    )
    assert sanitize_for_telegram("__importante__") == "importante"


def test_removes_headers():
    assert sanitize_for_telegram("# Título\nTexto") == "Título\nTexto"
    assert sanitize_for_telegram("### Sub\nok") == "Sub\nok"


def test_normalizes_asterisk_bullets():
    text = "* uno\n* dos"
    assert sanitize_for_telegram(text) == "- uno\n- dos"


def test_leaves_plain_text_untouched():
    plain = "Con tu peso de 82 kg, bebe unos 2,5 litros al día."
    assert sanitize_for_telegram(plain) == plain


def test_markdown_link_becomes_raw_url():
    text = "Mira [la ficha](https://world.openfoodfacts.org/product/123)"
    assert sanitize_for_telegram(text) == (
        "Mira https://world.openfoodfacts.org/product/123"
    )


def test_plain_url_is_preserved():
    text = "Ficha:\nhttps://world.openfoodfacts.org/product/123"
    assert sanitize_for_telegram(text) == text
