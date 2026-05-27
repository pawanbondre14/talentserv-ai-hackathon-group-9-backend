from app.services.vtt_parser import vtt_to_plain_text

SAMPLE = """WEBVTT

1
00:00:01.000 --> 00:00:05.000
Alex: Hello team.

2
00:00:05.500 --> 00:00:10.000
Jordan: Let's ship it.
"""


def test_vtt_to_plain_text():
    text = vtt_to_plain_text(SAMPLE)
    assert "Alex: Hello team." in text
    assert "Jordan: Let's ship it." in text
    assert "WEBVTT" not in text
    assert "-->" not in text
