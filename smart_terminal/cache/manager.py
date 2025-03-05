"""
Cache manager for SmartTerminal.

This module provides functionality to manage the command cache,
including saving, loading, and searching cache entries.
"""

import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Import for type checking, but handle case where models aren't available
try:
    from smart_terminal.cache.models import CacheEntry, CacheConfig

    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False


# Setup logging
logger = logging.getLogger(__name__)


class CacheManager:
    """
    Manages the command cache for SmartTerminal.

    This class provides methods for adding, retrieving, and maintaining
    cached command entries to improve performance and reduce API calls.
    """

    # Cache directory and file
    CACHE_DIR = Path.home() / ".smartterminal" / "cache"
    CACHE_FILE = CACHE_DIR / "commands.json"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the cache manager.

        Args:
            config: Optional cache configuration
        """
        self.config = config or {}
        self.enabled = self.config.get("cache_enabled", True)
        self.max_entries = self.config.get("cache_max_entries", 1000)
        self.max_age_days = self.config.get("cache_max_age_days", 30)
        self.min_similarity = self.config.get("cache_min_similarity", 0.85)
        self.fuzzy_matching = self.config.get("cache_fuzzy_matching", True)

        # Initialize cache
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._ensure_cache_dir()
        self._load_cache()

    def _ensure_cache_dir(self) -> None:
        """Ensure cache directory exists."""
        self.CACHE_DIR.mkdir(exist_ok=True, parents=True)

    def _load_cache(self) -> None:
        """Load cache from disk."""
        if not self.enabled:
            return

        try:
            if not self.CACHE_FILE.exists():
                # Create empty cache file
                with open(self.CACHE_FILE, "w") as f:
                    json.dump({}, f)
                return

            with open(self.CACHE_FILE, "r") as f:
                cache_data = json.load(f)

            # Convert to CacheEntry objects if models are available
            if MODELS_AVAILABLE:
                for key, entry in cache_data.items():
                    self.cache[key] = CacheEntry(**entry).model_dump()
            else:
                self.cache = cache_data

            logger.debug(f"Loaded {len(self.cache)} entries from cache")

            # Perform cache cleanup on load
            self._cleanup_cache()

        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            self.cache = {}

    def _save_cache(self) -> None:
        """Save cache to disk."""
        if not self.enabled:
            return

        try:
            self._ensure_cache_dir()

            # Convert CacheEntry objects to dictionaries if needed
            cache_dict = self.cache

            with open(self.CACHE_FILE, "w") as f:
                json.dump(cache_dict, f, indent=2)

            logger.debug(f"Saved {len(self.cache)} entries to cache")

        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def _compute_hash(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Compute a hash for the query and relevant context.

        Args:
            query: User query
            context: Optional context dictionary

        Returns:
            Hash string
        """
        # Extract only relevant context that would affect command generation
        relevant_context = {}
        if context:
            # Only include OS and directory info in hash
            if "default_os" in context:
                relevant_context["default_os"] = context["default_os"]
            if "directory" in context:
                dir_info = context["directory"]
                if isinstance(dir_info, dict) and "current_dir" in dir_info:
                    relevant_context["current_dir"] = dir_info["current_dir"]

        # Compute hash of query and relevant context
        hash_input = f"{query}|{json.dumps(relevant_context, sort_keys=True)}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    def _compute_similarity(self, query1: str, query2: str) -> float:
        """
        Compute similarity between two queries.

        Args:
            query1: First query
            query2: Second query

        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Simple case-insensitive comparison
        if query1.lower() == query2.lower():
            return 1.0

        # Try to import difflib for better similarity matching
        try:
            from difflib import SequenceMatcher

            return SequenceMatcher(None, query1.lower(), query2.lower()).ratio()
        except ImportError:
            # Fall back to simple character-based similarity
            query1_lower = query1.lower()
            query2_lower = query2.lower()

            # Find common characters
            common_chars = set(query1_lower) & set(query2_lower)

            # Calculate Jaccard similarity
            if not common_chars:
                return 0.0

            union_chars = set(query1_lower) | set(query2_lower)
            return len(common_chars) / len(union_chars)

    def _cleanup_cache(self) -> None:
        """Clean up old cache entries and enforce size limits."""
        if not self.enabled or not self.cache:
            return

        try:
            # Find entries that are too old
            now = datetime.now()
            max_age = timedelta(days=self.max_age_days)
            old_entries = []

            for key, entry in self.cache.items():
                created_at = entry.get("created_at")
                if not created_at:
                    continue

                # Convert string to datetime if needed
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.fromisoformat(created_at)
                    except ValueError:
                        continue

                if now - created_at > max_age:
                    old_entries.append(key)

            # Remove old entries
            for key in old_entries:
                del self.cache[key]

            logger.debug(f"Removed {len(old_entries)} old entries from cache")

            # Enforce size limit
            if len(self.cache) > self.max_entries:
                # Sort by access count and last accessed time
                entries = [
                    (k, v.get("access_count", 0), v.get("last_accessed"))
                    for k, v in self.cache.items()
                ]

                # Convert string to datetime for sorting if needed
                for i, (key, count, accessed) in enumerate(entries):
                    if isinstance(accessed, str):
                        try:
                            entries[i] = (key, count, datetime.fromisoformat(accessed))
                        except ValueError:
                            entries[i] = (key, count, now)

                # Sort by access count (ascending) and last accessed (ascending)
                entries.sort(key=lambda x: (x[1], x[2]))

                # Remove oldest entries
                entries_to_remove = entries[: len(self.cache) - self.max_entries]

                for key, _, _ in entries_to_remove:
                    del self.cache[key]

                logger.debug(
                    f"Removed {len(entries_to_remove)} least used entries from cache"
                )

            # Save changes
            self._save_cache()

        except Exception as e:
            logger.error(f"Error cleaning up cache: {e}")

    def add_to_cache(
        self,
        query: str,
        commands: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a command to the cache.

        Args:
            query: User query
            commands: Generated commands
            context: Optional context dictionary
        """
        if not self.enabled or not commands:
            return

        try:
            # Compute hash
            query_hash = self._compute_hash(query, context)

            # Get OS type from context or default to 'unknown'
            os_type = "unknown"
            if context:
                os_type = context.get("default_os", "unknown")

            # Create cache entry
            now = datetime.now()
            entry = {
                "query_hash": query_hash,
                "query": query,
                "commands": commands,
                "os_type": os_type,
                "created_at": now.isoformat(),
                "last_accessed": now.isoformat(),
                "access_count": 1,
            }

            # Add to cache
            self.cache[query_hash] = entry

            # Periodically save and clean up cache
            if len(self.cache) % 10 == 0:  # Save every 10 additions
                self._save_cache()
                self._cleanup_cache()

            logger.debug(f"Added entry to cache with hash {query_hash}")

        except Exception as e:
            logger.error(f"Error adding to cache: {e}")

    def get_from_cache(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get commands from cache if available.

        Args:
            query: User query
            context: Optional context dictionary

        Returns:
            List of commands if found in cache, None otherwise
        """
        if not self.enabled or not self.cache:
            return None

        try:
            # Check for exact match first
            query_hash = self._compute_hash(query, context)

            if query_hash in self.cache:
                entry = self.cache[query_hash]

                # Update access time and count
                now = datetime.now()
                entry["last_accessed"] = now.isoformat()
                entry["access_count"] = entry.get("access_count", 0) + 1

                logger.debug(f"Cache hit for hash {query_hash}")
                return entry["commands"]

            # If no exact match and fuzzy matching is enabled, try fuzzy matching
            if self.fuzzy_matching:
                best_match = None
                best_score = 0.0

                for entry_hash, entry in self.cache.items():
                    entry_query = entry.get("query", "")
                    if not entry_query:
                        continue

                    # Check if context OS matches entry OS
                    if context and context.get("default_os") != entry.get("os_type"):
                        continue

                    score = self._compute_similarity(query, entry_query)

                    if score > best_score and score >= self.min_similarity:
                        best_score = score
                        best_match = entry

                if best_match:
                    # Update access time and count
                    now = datetime.now()
                    best_match["last_accessed"] = now.isoformat()
                    best_match["access_count"] = best_match.get("access_count", 0) + 1

                    logger.debug(f"Fuzzy cache hit with score {best_score}")
                    return best_match["commands"]

            # No match found
            logger.debug("Cache miss")
            return None

        except Exception as e:
            logger.error(f"Error retrieving from cache: {e}")
            return None

    def clear_cache(self) -> bool:
        """
        Clear the entire cache.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.cache = {}
            self._save_cache()
            logger.info("Cache cleared")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the cache.

        Returns:
            Dictionary with cache statistics
        """
        stats = {
            "enabled": self.enabled,
            "entries": len(self.cache),
            "max_entries": self.max_entries,
            "max_age_days": self.max_age_days,
            "size_bytes": 0,
        }

        if self.CACHE_FILE.exists():
            stats["size_bytes"] = self.CACHE_FILE.stat().st_size

        # Compute hit rate if available
        hit_count = sum(
            entry.get("access_count", 0) > 1 for entry in self.cache.values()
        )
        if self.cache:
            stats["hit_rate"] = hit_count / len(self.cache)
        else:
            stats["hit_rate"] = 0.0

        return stats
