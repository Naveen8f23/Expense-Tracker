"""BACKLOG.md C8: the AI fallback seam always reports "unable to extract" for now."""

from app.domain.ai_fallback import StubAIFallbackClient


def test_stub_always_reports_unable_to_extract():
    client = StubAIFallbackClient()

    assert client.extract("anything at all") is None
    assert client.extract("") is None
