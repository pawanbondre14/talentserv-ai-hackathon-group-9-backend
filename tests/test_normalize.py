from app.services.normalize import normalize_transcript, word_count


def test_normalize_strips_html():
    raw = "<p>Hello <b>team</b></p>\n\nDecided to ship."
    assert "Hello" in normalize_transcript(raw)
    assert "<p>" not in normalize_transcript(raw)


def test_word_count():
    assert word_count("one two three") == 3
    assert word_count("") == 0
