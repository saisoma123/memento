# memento/region_store.py
from typing import Dict, Optional
from .region import Region
import json
import os

class RegionStore:
    def __init__(self):
        self.regions: Dict[str, Region] = {}

    def add(self, region: Region):
        self.regions[region.name] = region

    def get(self, name: str) -> Optional[Region]:
        return self.regions.get(name)

    def delete(self, name: str):
        if name in self.regions:
            del self.regions[name]

    def list(self) -> Dict[str, Region]:
        return self.regions

    def save_to_json(self, path: str):
        with open(path, 'w') as f:
            json.dump({name: r.to_dict() for name, r in self.regions.items()}, f, indent=2)

    @staticmethod
    def load_from_json(path: str) -> 'RegionStore':
        store = RegionStore()
        if not os.path.exists(path):
            return store
        with open(path, 'r') as f:
            data = json.load(f)
            for name, region_dict in data.items():
                store.add(Region.from_dict(region_dict))
        return store

    def summary(self) -> str:
        return f"RegionStore with {len(self.regions)} region(s):\n" + "\n".join(f"- {r.name} ({r.head[:8]})" for r in self.regions.values())
