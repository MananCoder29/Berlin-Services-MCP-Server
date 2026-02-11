import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

class LoopProtector:
    """Persistent memory to stop tool-re-execution loops in remote environments."""
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.hashes = self._load()
        
    def _load(self) -> Dict[str, Tuple[str, str, str]]:
        if not self.file_path.exists():
            return {}
        try:
            with open(self.file_path, "r") as f:
                data = json.load(f)
                # Cleanup old entries (> 24h)
                now = datetime.now()
                return {k: v for k, v in data.items() if (now - datetime.fromisoformat(v[0])).total_seconds() < 86400}
        except:
            return {}
            
    def save(self, key: str, path: str, file_id: str):
        self.hashes[key] = (datetime.now().isoformat(), path, file_id)
        try:
            with open(self.file_path, "w") as f:
                json.dump(self.hashes, f)
        except:
            pass

    def check(self, key: str) -> Optional[Tuple[str, str]]:
        if key in self.hashes:
            return self.hashes[key][1], self.hashes[key][2]
        return None
