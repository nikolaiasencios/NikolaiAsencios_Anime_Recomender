from unittest.mock import patch

from app.main import (
    extract_filters,
    build_explanation,
)


@patch("app.main.gemini_client")
def test_extract_filters_psychological(mock_client):

    mock_client.models.generate_content.return_value.text = """
    {
        "genres": ["Psychological"],
        "max_episodes": 30
    }
    """

    result = extract_filters(
        "Quiero un anime psicológico corto"
    )

    assert result["genres"] == ["Psychological"]
    assert result["max_episodes"] == 30


@patch("app.main.gemini_client")
def test_extract_filters_invalid_json(mock_client):

    mock_client.models.generate_content.return_value.text = (
        "texto invalido"
    )

    result = extract_filters("anime raro")

    assert result == {}


@patch("app.main.gemini_client")
def test_build_explanation_returns_text(
    mock_client
):

    mock_client.models.generate_content.return_value.text = (
        "Estas recomendaciones son adecuadas."
    )

    recommendations = [
        {
            "title": "Death Note"
        }
    ]

    result = build_explanation(
        "anime psicológico",
        recommendations
    )

    assert isinstance(result, str)
    assert len(result) > 0
