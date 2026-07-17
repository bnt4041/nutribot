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


def test_converts_markdown_table_to_plain_lines():
    text = (
        "Resumen:\n\n"
        "| | Totales | Objetivo | Te queda |\n"
        "|---|---|---|---|\n"
        "| 🔥 Calorías | 1179 / 1200 | 1200 | 21 kcal |\n"
        "| 💧 Agua | 400 / 3630ml | 3630ml | 3230ml |\n\n"
        "Buen trabajo."
    )
    out = sanitize_for_telegram(text)
    assert "|" not in out
    assert "---" not in out
    assert "🔥 Calorías — Totales: 1179 / 1200 · Objetivo: 1200 · Te queda: 21 kcal" in out
    assert "💧 Agua — Totales: 400 / 3630ml · Objetivo: 3630ml · Te queda: 3230ml" in out
    assert out.startswith("Resumen:")
    assert out.endswith("Buen trabajo.")


def test_converts_two_column_table():
    text = "| Campo | Valor |\n|---|---|\n| Peso | 82 kg |\n| Altura | 180 cm |"
    out = sanitize_for_telegram(text)
    assert out == "Peso — Valor: 82 kg\nAltura — Valor: 180 cm"


def test_table_without_leading_pipes_is_also_converted():
    text = "Campo | Valor\n---|---\nPeso | 82 kg"
    out = sanitize_for_telegram(text)
    assert out == "Peso — Valor: 82 kg"


# The exact block observed leaking into Telegram (fullwidth-pipe wrappers).
_LEAKED = (
    "Voy a confirmarla ya que has dicho que sí.\n"
    "<｜DSML｜｜tool_calls｜>\n"
    '<｜DSML｜｜invoke name="update_diet_plan_item">\n'
    '<｜DSML｜｜parameter name="item_id" string="false">51<｜/｜｜DSML｜｜parameter>\n'
    '<｜DSML｜｜parameter name="status" string="true">confirmed<｜/｜｜DSML｜｜parameter>\n'
    "<｜/｜｜DSML｜｜invoke>\n"
    "<｜/｜｜DSML｜｜tool_calls>"
)


def test_strips_leaked_tool_call_block():
    out = sanitize_for_telegram(_LEAKED)
    assert out == "Voy a confirmarla ya que has dicho que sí."
    for token in ("DSML", "tool_calls", "invoke", "parameter", "51", "confirmed"):
        assert token not in out


def test_strips_ascii_rendered_tool_call_block():
    text = (
        "Hecho.\n"
        "< | DSML | | tool_calls>\n"
        '< | DSML | | invoke name="log_meal">\n'
        '< | DSML | | parameter name="food_name" string="true">café</ | DSML | | parameter>\n'
        "</ | DSML | | invoke>\n"
        "</ | DSML | | tool_calls>"
    )
    out = sanitize_for_telegram(text)
    assert out == "Hecho."
