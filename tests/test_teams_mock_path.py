"""Mock transcript path must not allow directory traversal."""

import pytest

from app.services.teams_service import TeamsService


def test_resolve_mock_transcript_rejects_traversal():
    svc = TeamsService.__new__(TeamsService)
    with pytest.raises(ValueError, match="Invalid transcript_file"):
        svc._resolve_mock_transcript_path("../../.env")
