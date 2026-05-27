"""Upload route accepts .txt and .vtt."""

from app.routes.ingest import _parse_upload_body

SAMPLE_VTT = """WEBVTT

00:00:01.000 --> 00:00:05.000
Interviewer: Hello there.

00:00:05.000 --> 00:00:10.000
Candidate: Thanks for having me.
"""


def test_parse_upload_body_vtt_extension():
    text = _parse_upload_body(SAMPLE_VTT, ".vtt")
    assert "Interviewer: Hello there." in text
    assert "WEBVTT" not in text


def test_parse_upload_body_txt_passthrough():
    body = "Plain transcript line one."
    assert _parse_upload_body(body, ".txt") == body
