"""
Cache Disk Adapter - Implements CachePort using disk-based storage.
"""

from __future__ import annotations
import json
import hashlib
import time
from typing import Any, Optional
from pathlib import Path

from src.domain.ports import CachePort, LoggerPort
from src.infrastructure.config.settings import CacheSettings


class CacheDiskAdapter(CachePort):
    """Disk-based cache implementation."""
    
    def __init__(self, settings: CacheSettings, logger: LoggerPort) -> None:
        self.settings = settings
        self.logger = logger
        self.cache_dir = Path(settings.directory)
        self.ttl_seconds = settings.ttl_hours * 3600
        
        # Create cache directories
        self.cache_dir.mkdir(exist_ok=True)
        (self.cache_dir / "data").mkdir(exist_ok=True)
        (self.cache_dir / "metadata").mkdir(exist_ok=True)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.settings.enabled:
            return None
        
        try:
            cache_file = self._get_cache_file(key)
            metadata_file = self._get_metadata_file(key)
            
            if not cache_file.exists() or not metadata_file.exists():
                return None
            
            # Check TTL
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            created_at = metadata.get("created_at", 0)
            if time.time() - created_at > self.ttl_seconds:
                # Cache expired, cleanup
                await self.delete(key)
                return None
            
            # Load cached value
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            self.logger.debug(f"Cache hit for key: {key[:50]}...")
            return data
            
        except Exception as e:
            self.logger.warning(f"Cache read failed for key {key[:50]}...: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set value in cache with optional TTL."""
        if not self.settings.enabled:
            return
        
        try:
            cache_file = self._get_cache_file(key)
            metadata_file = self._get_metadata_file(key)
            
            # Save data
            with open(cache_file, 'w') as f:
                json.dump(value, f)
            
            # Save metadata
            metadata = {
                "created_at": time.time(),
                "ttl_seconds": ttl_seconds or self.ttl_seconds,
                "key": key
            }
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f)
            
            self.logger.debug(f"Cache set for key: {key[:50]}...")
            
        except Exception as e:
            self.logger.warning(f"Cache write failed for key {key[:50]}...: {e}")
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.settings.enabled:
            return False
        
        cache_file = self._get_cache_file(key)
        metadata_file = self._get_metadata_file(key)
        
        if not cache_file.exists() or not metadata_file.exists():
            return False
        
        # Check TTL
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            created_at = metadata.get("created_at", 0)
            ttl = metadata.get("ttl_seconds", self.ttl_seconds)
            
            if time.time() - created_at > ttl:
                # Cache expired
                await self.delete(key)
                return False
            
            return True
            
        except Exception:
            return False
    
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        try:
            cache_file = self._get_cache_file(key)
            metadata_file = self._get_metadata_file(key)
            
            cache_file.unlink(missing_ok=True)
            metadata_file.unlink(missing_ok=True)
            
            self.logger.debug(f"Cache deleted for key: {key[:50]}...")
            
        except Exception as e:
            self.logger.warning(f"Cache delete failed for key {key[:50]}...: {e}")
    
    def generate_key(self, *args: Any) -> str:
        """Generate deterministic cache key from arguments."""
        # Convert all arguments to string and create hash
        key_parts = []
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            elif isinstance(arg, (list, dict)):
                key_parts.append(json.dumps(arg, sort_keys=True))
            else:
                key_parts.append(str(arg))
        
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for key."""
        return self.cache_dir / "data" / f"{key}.json"
    
    def _get_metadata_file(self, key: str) -> Path:
        """Get metadata file path for key."""
        return self.cache_dir / "metadata" / f"{key}.meta.json"