"""
Data models for the caching system.

This module defines the data structures used by the caching system.
"""

from datetime import datetime
from typing import List, Dict, Any
from pydantic import BaseModel, Field


class CacheEntry(BaseModel):
    """
    Represents a cached command entry.

    This model stores information about a cached command, including the
    original query, generated commands, and metadata.
    """

    query_hash: str = Field(..., description="Hash of the user query")
    query: str = Field(..., description="Original user query")
    commands: List[Dict[str, Any]] = Field(..., description="Generated commands")
    os_type: str = Field(..., description="OS type for which commands were generated")
    created_at: datetime = Field(
        default_factory=datetime.now, description="When this entry was created"
    )
    last_accessed: datetime = Field(
        default_factory=datetime.now, description="When this entry was last accessed"
    )
    access_count: int = Field(
        default=1, description="Number of times this entry has been accessed"
    )

    def update_access(self) -> None:
        """Update the last accessed time and increment access count."""
        self.last_accessed = datetime.now()
        self.access_count += 1


class CacheConfig(BaseModel):
    """
    Configuration for the caching system.

    This model defines the settings that control the behavior of the cache.
    """

    enabled: bool = Field(default=True, description="Whether caching is enabled")
    max_entries: int = Field(
        default=1000, description="Maximum number of entries to store in cache"
    )
    max_age_days: int = Field(
        default=30, description="Maximum age of cache entries in days"
    )
    min_similarity: float = Field(
        default=0.85, description="Minimum similarity score for fuzzy matching"
    )
    fuzzy_matching: bool = Field(
        default=True, description="Whether to enable fuzzy matching for queries"
    )
