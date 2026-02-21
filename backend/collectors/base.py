"""
Base classes for collectors – SearchProvider interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str
    published_date: Optional[str] = None  # YYYY-MM-DD or YYYY-MM or YYYY
    source_domain: str = ""
    question_id: str = ""
    query: str = ""


class SearchProvider(ABC):
    """Pluggable search provider interface."""

    @abstractmethod
    async def search(self, query: str, num_results: int = 10) -> List[SearchResult]:
        """Return a list of search results for the given query."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        ...
