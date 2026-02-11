from typing import List

def expand_query(query: str) -> List[str]:
    """Helper to expand query with synonyms and split into terms."""
    query_lower = query.lower()
    synonyms = {
        "deregister": "abmeldung",
        "un-register": "abmeldung",
        "register": "anmeldung",
        "registration": "anmeldung",
        "housing": "wohnung",
        "apartment": "wohnung",
        "birth": "geburt",
        "death": "sterbefall",
        "marriage": "ehe",
        "identity": "ausweis",
        "passport": "pass",
        "business": "gewerbe",
        "vehicle": "kfz",
        "car": "kfz",
        "driver": "fahrer",
        "license": "erlaubnis",
        "parking": "parken",
        "resident": "bewohner"
    }
    
    expanded = query_lower
    for eng, ger in synonyms.items():
        if eng in query_lower:
            expanded += f" {ger}"
    return expanded.split()
