"""Tests for recovering tool calls the model leaks as plain text."""

from app.services.deepseek.leaked_tools import parse_leaked_tool_calls


def test_parses_leaked_update_call():
    text = (
        "Voy a confirmarla.\n"
        "<｜DSML｜｜tool_calls｜>\n"
        '<｜DSML｜｜invoke name="update_diet_plan_item">\n'
        '<｜DSML｜｜parameter name="item_id" string="false">51<｜/｜｜DSML｜｜parameter>\n'
        '<｜DSML｜｜parameter name="status" string="true">confirmed<｜/｜｜DSML｜｜parameter>\n'
        "<｜/｜｜DSML｜｜invoke>\n"
        "<｜/｜｜DSML｜｜tool_calls>"
    )
    calls = parse_leaked_tool_calls(text)
    assert calls == [
        ("update_diet_plan_item", {"item_id": 51, "status": "confirmed"}),
    ]


def test_coerces_value_types():
    text = (
        '<invoke name="log_meal">'
        '<parameter name="food_name">café con leche</parameter>'
        '<parameter name="calories">120</parameter>'
        '<parameter name="protein_g">4.5</parameter>'
        "</invoke>"
    )
    (name, args), = parse_leaked_tool_calls(text)
    assert name == "log_meal"
    assert args == {
        "food_name": "café con leche",
        "calories": 120,
        "protein_g": 4.5,
    }


def test_parses_multiple_invokes():
    text = (
        '<invoke name="get_diet_plan"></invoke>'
        '<invoke name="remove_diet_plan_item">'
        '<parameter name="item_id">7</parameter></invoke>'
    )
    calls = parse_leaked_tool_calls(text)
    assert calls == [
        ("get_diet_plan", {}),
        ("remove_diet_plan_item", {"item_id": 7}),
    ]


def test_plain_text_yields_no_calls():
    assert parse_leaked_tool_calls("Con gusto, aquí tienes tu resumen.") == []
    assert parse_leaked_tool_calls("") == []
    assert parse_leaked_tool_calls(None) == []
