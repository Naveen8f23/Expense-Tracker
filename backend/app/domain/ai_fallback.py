"""AIFallbackClient interface (BACKLOG.md C8; Constitution principle 10; REQUIREMENTS.md
EXT-3/EXT-4).

Defines the seam between the deterministic extraction pipeline (app/domain/extraction.py) and a
future AI-based fallback for an email from a known sender whose content doesn't match any known
content pattern, or whose fixed parser fails despite matching. The extraction module doesn't need
to know which implementation produced a result -- only whether one exists.

The stub implementation always reports "unable to extract" (returns None), which routes the email
to the needs-review queue (BACKLOG.md C7, EXT-6) rather than guessing. This proves the seam works
without committing to a provider; swapping in a real implementation later requires no changes
outside the Infrastructure layer (Constitution principle 10).
"""

from typing import Optional, Protocol

from app.domain.extraction import ExtractedTransaction


class AIFallbackClient(Protocol):
    def extract(self, content: str) -> Optional[ExtractedTransaction]:
        """Best-effort extraction from raw email content.

        Returns None ("unable to extract") rather than raising, so callers can treat "no fallback
        available" and "fallback declined to guess" identically -- both mean needs-review.
        """
        ...


class StubAIFallbackClient:
    """Always reports "unable to extract" -- no real provider is chosen yet (REQUIREMENTS.md
    SS4 NFR Security -- AI processing)."""

    def extract(self, content: str) -> Optional[ExtractedTransaction]:
        return None
