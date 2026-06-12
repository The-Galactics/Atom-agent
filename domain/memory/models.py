from dataclasses import dataclass


@dataclass
class MemoryEntry:
    content: str
    metadata: dict
    score: float | None = None
