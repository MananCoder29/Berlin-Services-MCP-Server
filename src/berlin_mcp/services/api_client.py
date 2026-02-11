import httpx
from datetime import datetime
from typing import Dict, Tuple
from ..config import BASE_URL, CACHE_DURATION_SECONDS, CACHE_FILE, logger
from .cache import CacheManager

_cache = CacheManager(CACHE_FILE, CACHE_DURATION_SECONDS)

FALLBACK_DATA = {
    "data": [
        {
            "id": "120686",
            "name": "Anmeldung einer Wohnung",
            "description": "Registration of residence",
            "meta": {"keywords": "anmeldung,wohnung", "url": "https://service.berlin.de/dienstleistung/120686/"},
            "fees": "EUR 0.00",
            "onlineservices": [],
            "locations": [],
            "requirements": [],
            "forms": []
        },
        {
            "id": "121468",
            "name": "Reisepass (Passport)",
            "description": "Application for German passport",
            "meta": {"keywords": "reisepass,passport", "url": "https://service.berlin.de/dienstleistung/121468/"},
            "fees": "EUR 60.00",
            "onlineservices": [],
            "locations": [],
            "requirements": [],
            "forms": []
        },
        {
            "id": "120335",
            "name": "Führerschein",
            "description": "Driver's license",
            "meta": {"keywords": "führerschein,driver", "url": "https://service.berlin.de/dienstleistung/120335/"},
            "fees": "EUR 43.00",
            "onlineservices": [],
            "locations": [],
            "requirements": [],
            "forms": []
        }
    ],
    "created": datetime.now().isoformat(),
    "hash": "fallback_v1"
}

async def fetch_services_data(force_refresh: bool = False) -> Tuple[Dict, str]:
    """
    Fetch services with intelligent fallback strategy.
    
    Returns:
        Tuple of (data, source) where source is 'live', 'memory', 'disk', or 'fallback'
    """
    
    # Try memory cache
    if not force_refresh:
        data, valid = _cache.get_memory()
        if valid:
            return data, "memory"
    
    # Try live API
    try:
        logger.info("Fetching from live API")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(BASE_URL)
            response.raise_for_status()
            data = response.json()
            
            if data.get("data") and isinstance(data["data"], list):
                _cache.set(data)
                logger.info(f"Live API: {len(data['data'])} services fetched")
                return data, "live"
    except Exception as e:
        logger.warning(f"Live API failed: {e}")
    
    # Try disk cache
    if not force_refresh:
        data, valid = _cache.get_disk()
        if data:
            return data, "disk"
    
    # Fallback to embedded data
    logger.warning("Using fallback data")
    return FALLBACK_DATA, "fallback"

def get_cache_instance() -> CacheManager:
    return _cache
