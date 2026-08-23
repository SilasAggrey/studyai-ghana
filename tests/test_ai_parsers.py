"""JSON extraction from messy LLM output."""
import pytest

from app.ai.base import AIProviderError
from app.ai.parsers import extract_json, extract_json_array


def test_extract_plain_object():
    value = extract_json('{"a": 1, "b": [1, 2]}')
    assert value == {"a": 1, "b": [1, 2]}


def test_extract_from_code_fence():
    text = 'Sure! Here is the result:\n```json\n{"ok": true}\n```\nHope it helps.'
    assert extract_json(text) == {"ok": True}


def test_extract_array_with_prose():
    text = "Here you go: [{\"q\": 1}, {\"q\": 2}] — please review."
    assert extract_json_array(text) == [{"q": 1}, {"q": 2}]


def test_extract_wrapped_questions_key():
    text = '{"questions": [{"q": 1}, {"q": 2}]}'
    assert extract_json_array(text) == [{"q": 1}, {"q": 2}]


def test_extract_leading_text():
    assert extract_json('prefix {"x": "y"} suffix') == {"x": "y"}


def test_invalid_json_raises():
    with pytest.raises(AIProviderError):
        extract_json("no json here")


def test_unterminated_json_raises():
    with pytest.raises(AIProviderError):
        extract_json('{"a": [1, 2')


def test_empty_response_raises():
    with pytest.raises(AIProviderError):
        extract_json("")
