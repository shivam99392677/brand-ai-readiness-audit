"""Deterministic Evidence ID Generator for Brand AI Readiness Extraction Layer."""

from typing import Optional


class EvidenceIdGenerator:
    """Centralized, deterministic Evidence ID generator.
    
    Generates sequentially formatted IDs like EV-00001, EV-00002, etc.
    Guarantees no collisions across extractors and strictly deterministic ordering.
    """

    def __init__(self, prefix: str = "EV-", digits: int = 5, start: int = 1):
        self.prefix = prefix
        self.digits = digits
        self.start = start
        self._counter = start

    def next_id(self) -> str:
        """Generates the next deterministic evidence ID and increments the internal counter."""
        evidence_id = f"{self.prefix}{str(self._counter).zfill(self.digits)}"
        self._counter += 1
        return evidence_id

    def reset(self, start: Optional[int] = None):
        """Resets the internal counter back to initial or specified value."""
        self._counter = start if start is not None else self.start

    @property
    def current_count(self) -> int:
        """Returns the number of IDs generated so far."""
        return self._counter - self.start
