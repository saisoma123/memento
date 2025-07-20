# memento/region.py
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class Region:
    name: str                      # Region identifier (e.g., "Planner")
    head: str                      # ID of the most recent event node
    root: Optional[str] = None     # ID of the root event (optional)
    meta: Optional[Dict] = None    # Arbitrary metadata (agent type, task, tags, etc.)

    def to_dict(self):
        return {
            "name": self.name,
            "head": self.head,
            "root": self.root,
            "meta": self.meta or {}
        }

    @staticmethod
    def from_dict(d):
        return Region(
            name=d["name"],
            head=d["head"],
            root=d.get("root"),
            meta=d.get("meta", {})
        )

    def summary(self) -> str:
        return f"Region '{self.name}'\n - Head: {self.head[:8]}\n - Root: {self.root[:8] if self.root else 'N/A'}\n - Meta: {self.meta}"
