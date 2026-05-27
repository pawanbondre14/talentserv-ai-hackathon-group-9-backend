import os

import pytest

from app.config import get_settings
from app.services.llm import parse_json_response, process_transcript

get_settings.cache_clear()


def test_parse_json_with_fences():
    raw = '```json\n{"executive_summary": "ok"}\n```'
    data = parse_json_response(raw)
    assert data["executive_summary"] == "ok"


def test_process_mock_meeting():
    os.environ["LLM_MOCK"] = "true"
    get_settings.cache_clear()
    settings = get_settings()
    result = process_transcript(settings, "meeting", "word " * 60)
    assert "executive_summary" in result
    assert "action_items" in result
    os.environ.pop("LLM_MOCK", None)
    get_settings.cache_clear()
