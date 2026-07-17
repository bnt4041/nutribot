"""Tests for detecting replies that claim a mutation with no tool call behind it."""

from app.services.deepseek.hallucination_guard import looks_like_unbacked_action_claim


def test_flags_narrated_steps_and_fake_confirmation():
    text = (
        "Voy a consultar el plan actual para hacer los cambios.\n"
        "Primero veo los IDs de lo que hay.\n"
        "Vale, veo el plan. El desayuno del sábado tiene id 19. Lo voy a modificar.\n"
        "Calculo macros aproximados: ...\n"
        "Lo actualizo.\n"
        "Hecho. Tu sábado queda así: Desayuno 09:00: Medio mollete con jamón ✅"
    )
    assert looks_like_unbacked_action_claim(text) is True


def test_flags_bare_completion_claim():
    assert looks_like_unbacked_action_claim("Listo, ya está actualizado ✅") is True
    assert looks_like_unbacked_action_claim("Confirmada la comida del viernes.") is True


def test_leaves_plain_informational_reply_alone():
    text = "Con tu peso de 82 kg, bebe unos 2,5 litros al día."
    assert looks_like_unbacked_action_claim(text) is False


def test_leaves_plain_question_alone():
    text = "Claro, dime que desayuno te apetece el domingo."
    assert looks_like_unbacked_action_claim(text) is False


def test_empty_text_is_not_flagged():
    assert looks_like_unbacked_action_claim("") is False
