from dataclasses import dataclass


@dataclass
class MemoryEntry:
    # Retrieved semantic memory item from vector store.
    content: str
    metadata: dict
    score: float | None = None
