from typing import Dict
from ..models import ServiceCategory, CATEGORY_KEYWORDS

def categorize_service(service: Dict) -> ServiceCategory:
    """Categorize a service based on its content"""
    name = service.get("name", "").lower()
    keywords = service.get("meta", {}).get("keywords", "").lower()
    full_text = f"{name} {keywords}".lower()
    
    for category, keywords_list in CATEGORY_KEYWORDS.items():
        if any(kw in full_text for kw in keywords_list):
            return category
    
    return ServiceCategory.OTHER
