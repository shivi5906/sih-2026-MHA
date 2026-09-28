from __future__ import annotations
import hashlib
import json
import logging
import shutil
from pathlib import Path
from typing import Any

from vaultx.config import Config
from vaultx.providers.base import DataProvider

logger = logging.getLogger(__name__)

class CachingProvider(DataProvider):
    """Record-replay caching layer wrapping another DataProvider."""
    
    def __init__(self, provider: DataProvider, config: Config) -> None:
        self.provider = provider
        self.config = config
        cache_dir_str = getattr(config, 'cache_dir', '.cache')
        self.cache_dir = Path(cache_dir_str)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._hits = 0
        self._misses = 0

    def _generate_cache_key(self, chain: str, endpoint: str, params: dict[str, Any] | None) -> str:
        """Generate a SHA-256 cache key based on the request parameters."""
        params_str = json.dumps(params or {}, sort_keys=True)
        key_content = f"{chain}:{endpoint}:{params_str}"
        return hashlib.sha256(key_content.encode('utf-8')).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the file path for the cache key."""
        return self.cache_dir / f"{cache_key}.json"

    async def fetch(self, chain: str, endpoint: str, params: dict[str, Any] | None = None,
                    headers: dict[str, str] | None = None) -> dict[str, Any]:
        """Fetch data from cache, or delegate to wrapped provider and cache the result."""
        cache_key = self._generate_cache_key(chain, endpoint, params)
        cache_path = self._get_cache_path(cache_key)
        
        if cache_path.exists():
            logger.debug(f"Cache hit for {chain} {endpoint}")
            self._hits += 1
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        logger.debug(f"Cache miss for {chain} {endpoint}")
        self._misses += 1
        
        # Delegate to wrapped provider
        data = await self.provider.fetch(chain, endpoint, params, headers)
        
        # Save to cache using atomic write
        temp_path = cache_path.with_suffix('.tmp')
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        
        temp_path.replace(cache_path)
            
        return data

    async def close(self) -> None:
        """Close the wrapped provider."""
        await self.provider.close()
        
    def clear_cache(self) -> None:
        """Clear all cached responses."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._hits = 0
            self._misses = 0
            logger.info("Cache cleared.")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache hit count, miss count, and total size."""
        total_size = sum(f.stat().st_size for f in self.cache_dir.glob('**/*') if f.is_file())
        return {
            'hits': self._hits,
            'misses': self._misses,
            'total_size_bytes': total_size
        }
