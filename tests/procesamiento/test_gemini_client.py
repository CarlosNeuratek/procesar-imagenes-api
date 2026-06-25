"""Gemini client wrapper tests — text path + str(response) fallback."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_generate_returns_response_text() -> None:
    from app.procesamiento import gemini_client
    from app.procesamiento.gemini_client import generate

    fake_response = MagicMock()
    fake_response.text = "the cat sat on the mat"

    with patch.object(gemini_client, "_get_client") as gc:
        gc.return_value.models.generate_content.return_value = fake_response
        out = generate("describe", b"fake-bytes", "image/jpeg")

    assert out == "the cat sat on the mat"
    gc.return_value.models.generate_content.assert_called_once()
    kwargs = gc.return_value.models.generate_content.call_args.kwargs
    assert kwargs["model"] == "gemini-2.5-flash"


def test_generate_falls_back_to_str_when_text_raises() -> None:
    from app.procesamiento import gemini_client
    from app.procesamiento.gemini_client import generate

    fake_response = MagicMock()
    type(fake_response).text = property(
        lambda self: (_ for _ in ()).throw(ValueError("blocked"))
    )

    with patch.object(gemini_client, "_get_client") as gc:
        gc.return_value.models.generate_content.return_value = fake_response
        out = generate("describe", b"fake", "image/png")

    # str(MagicMock) is a stable string, just confirm it didn't raise.
    assert isinstance(out, str)
    assert out != ""