"""
Caching system for SmartTerminal.

This module provides functionality to cache command generation results,
reducing API calls and improving performance for repeated tasks.
"""

from smart_terminal.cache.manager import CacheManager
from smart_terminal.cache.models import CacheEntry, CacheConfig

__all__ = ["CacheManager", "CacheEntry", "CacheConfig"]
