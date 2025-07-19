# memento_mvp_runtime.py
# MVP of the Memento LLM memory runtime (log-based, Merkle-DAG, forkable)

import hashlib
import json
import time
import os
from typing import List, Optional, Dict

def structural_hash(event: dict) -> str:
    """Returns a stable hash of a structured event."""
    event_json = json.dumps(event, sort_keys=True).encode()
    return hashlib.blake2b(event_json, digest_size=8).hexdigest()

def merkle_root(hashes: List[str]) -> str:
    if not hashes:
        return ""
    while len(hashes) > 1:
        new_level = []
        for i in range(0, len(hashes), 2):
            left = hashes[i]
            right = hashes[i + 1] if i + 1 < len(hashes) else left
            new_hash = hashlib.blake2b((left + right).encode(), digest_size=8).hexdigest()
            new_level.append(new_hash)
        hashes = new_level
    return hashes[0]

class Region:
    def __init__(self, name: str, parent: Optional['Region'] = None, meta: Optional[Dict[str, str]] = None):
        self.name = name
        self.parent = parent
        self.meta = meta or {}
        self.events: List[dict] = []
        self.hashes: List[str] = []
        self.created_at = time.time()

    def observe(self, content: str):
        self._append_event("observe", content)

    def plan(self, content: str):
        self._append_event("plan", content)

    def effect(self, tool: str, result: str):
        self._append_event("effect", f"{tool}: {result}")

    def summarize(self, content: str):
        self._append_event("summarize", content)

    def _append_event(self, op: str, content: str):
        event = {
            "op": op,
            "content": content,
            "timestamp": time.time(),
            "agent": self.name,
            "meta": self.meta
        }
        self.events.append(event)
        self.hashes.append(structural_hash(event))

    def root_hash(self) -> str:
        return merkle_root(self.hashes)

    def fork(self, name: Optional[str] = None) -> 'Region':
        fork_name = name or f"{self.name}-fork"
        new_region = Region(fork_name, parent=self, meta=self.meta.copy())
        new_region.events = list(self.events)
        new_region.hashes = list(self.hashes)
        return new_region

    def diff(self, other: 'Region') -> List[str]:
        return [h for h in other.hashes if h not in self.hashes]

    def replay(self):
        return [e for e in self.events]

    def summary(self) -> str:
        return f"Region '{self.name}' with {len(self.events)} events. Root hash: {self.root_hash()}"

    def save_to_disk(self, directory: str):
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, f"{self.name}.jsonl")
        with open(path, "w") as f:
            for event in self.events:
                f.write(json.dumps(event) + "\n")

    @classmethod
    def load_from_disk(cls, path: str) -> 'Region':
        name = os.path.splitext(os.path.basename(path))[0]
        region = cls(name)
        with open(path, "r") as f:
            for line in f:
                event = json.loads(line.strip())
                region.events.append(event)
                region.hashes.append(structural_hash(event))
                region.meta = event.get("meta", {})
        return region

# Sample usage
if __name__ == "__main__":
    r1 = Region("Planner", meta={"agent_type": "planner", "task": "loan_approval"})
    r1.observe("User requested a loan")
    r1.plan("Check credit score and income")
    r1.effect("credit_api", "score: 720")
    r1.summarize("User is eligible")

    print(r1.summary())

    r1.save_to_disk("logs")
    loaded = Region.load_from_disk("logs/Planner.jsonl")
    print("Loaded:", loaded.summary())

    r2 = r1.fork("RetryPlanner")
    r2.plan("Try with updated income")
    r2.effect("income_api", "income: 80k")
    print(r2.summary())
    print("Diff from fork:", r1.diff(r2))
