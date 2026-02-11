import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple
from ..config import logger

class CacheManager:
    """Intelligent cache with persistent disk storage"""
    
    def __init__(self, cache_file: Path, ttl: int):
        self.cache_file = cache_file
        self.ttl = ttl
        self._memory_cache: Optional[Dict] = None
        self._memory_timestamp: Optional[datetime] = None
    
    def is_valid(self, timestamp: Optional[datetime]) -> bool:
        """Check if cache timestamp is still valid"""
        if not timestamp:
            return False
        age = (datetime.now() - timestamp).total_seconds()
        return age < self.ttl
    
    def get_memory(self) -> Tuple[Optional[Dict], bool]:
        """Get data from memory cache"""
        if self.is_valid(self._memory_timestamp):
            logger.debug("Memory cache hit")
            return self._memory_cache, True
        return None, False
    
    def get_disk(self) -> Tuple[Optional[Dict], bool]:
        """Get data from disk cache"""
        if not self.cache_file.exists():
            return None, False
        
        try:
            with open(self.cache_file, 'r') as f:
                cached = json.load(f)
            
            timestamp = datetime.fromisoformat(cached.get('_timestamp', ''))
            if self.is_valid(timestamp):
                logger.debug("Disk cache hit")
                return cached['data'], True
        except Exception as e:
            logger.warning(f"Disk cache read error: {e}")
        
        return None, False
    
    def set(self, data: Dict):
        """Store in both memory and disk cache"""
        self._memory_cache = data
        self._memory_timestamp = datetime.now()
        
        try:
            with open(self.cache_file, 'w') as f:
                json.dump({
                    'data': data,
                    '_timestamp': datetime.now().isoformat()
                }, f)
            logger.debug("Data cached to disk and memory")
        except Exception as e:
            logger.warning(f"Disk cache write error: {e}")
    
    def clear(self):
        """Clear all caches"""
        self._memory_cache = None
        self._memory_timestamp = None
        if self.cache_file.exists():
            self.cache_file.unlink()
        logger.info("Cache cleared")
