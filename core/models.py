"""Shared domain models for collected evidence and pipeline metadata."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class EvidenceItem:
    """A normalized, traceable item collected from one source."""

    source_id: str
    source_name: str
    title: str
    url: str
    published_at: str = ""
    summary: str = ""
    author: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SourceResult:
    """Collection result for a configured source."""

    source_name: str
    display_name: str
    source_url: str
    status: str
    items: list[EvidenceItem] = field(default_factory=list)
    error: str = ""
    collected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "display_name": self.display_name,
            "source_url": self.source_url,
            "status": self.status,
            "items": [item.to_dict() for item in self.items],
            "error": self.error,
            "collected_at": self.collected_at,
        }
