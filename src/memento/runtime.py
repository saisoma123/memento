# memento_mvp_runtime.py
# MVP of the Memento LLM memory runtime (log-based, Merkle-DAG, forkable, GC/versioning)

import hashlib
import json
import time
import os
import sqlite3
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
    HEADS: Dict[str, 'Region'] = {}

    def __init__(self, name: str, parent: Optional['Region'] = None, meta: Optional[Dict[str, str]] = None):
        self.name = name
        self.parent = parent
        self.meta = meta or {}
        self.events: List[dict] = []
        self.hashes: List[str] = []
        self.created_at = time.time()
        Region.HEADS[self.name] = self

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
        Region.HEADS[self.name] = self  # Update HEAD

    def root_hash(self) -> str:
        return merkle_root(self.hashes)

    def fork(self, name: Optional[str] = None) -> 'Region':
        fork_name = name or f"{self.name}-fork"
        new_region = Region(fork_name, parent=self, meta=self.meta.copy())
        new_region.events = list(self.events)
        new_region.hashes = list(self.hashes)
        return new_region

    def merge(self, other: 'Region', name: Optional[str] = None) -> 'Region':
        """Merge two regions into a new region, deduplicating identical events."""
        merge_name = name or f"{self.name}_MERGED_{other.name}"
        merged = Region(merge_name, meta={**self.meta, **other.meta})

        combined = self.events + other.events
        seen_hashes = set()
        for event in sorted(combined, key=lambda e: e["timestamp"]):
            h = structural_hash(event)
            if h not in seen_hashes:
                merged.events.append(event)
                merged.hashes.append(h)
                seen_hashes.add(h)

        return merged

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
        Region.HEADS[name] = region
        return region

    def save_to_sqlite(self, db_path: str):
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('DELETE FROM events WHERE region = ?', (self.name,))
        c.execute('''CREATE TABLE IF NOT EXISTS events (
                        region TEXT,
                        timestamp REAL,
                        op TEXT,
                        content TEXT,
                        meta TEXT,
                        hash TEXT
                     )''')
        c.execute('''CREATE TABLE IF NOT EXISTS heads (
                        region TEXT PRIMARY KEY,
                        timestamp REAL
                     )''')
        for event, h in zip(self.events, self.hashes):
            c.execute('''INSERT INTO events (region, timestamp, op, content, meta, hash)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (self.name, event["timestamp"], event["op"], event["content"], json.dumps(event["meta"]), h))
        # Update HEAD
        c.execute('''INSERT OR REPLACE INTO heads (region, timestamp)
                     VALUES (?, ?)''', (self.name, self.created_at))
        conn.commit()
        conn.close()

    @classmethod
    def load_from_sqlite(cls, db_path: str, region_name: str) -> 'Region':
        region = cls(region_name)
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute('''SELECT timestamp, op, content, meta FROM events WHERE region = ? ORDER BY timestamp''', (region_name,))
        for row in c.fetchall():
            timestamp, op, content, meta_json = row
            meta = json.loads(meta_json)
            event = {
                "timestamp": timestamp,
                "op": op,
                "content": content,
                "meta": meta,
                "agent": region_name
            }
            region.events.append(event)
            region.hashes.append(structural_hash(event))
            region.meta = meta
        Region.HEADS[region_name] = region
        conn.close()
        return region

    @classmethod
    def gc(cls, keep: List[str]):
        """Garbage collect unused region versions not in keep list."""
        to_delete = [r for r in cls.HEADS if r not in keep]
        for r in to_delete:
            del cls.HEADS[r]

    @classmethod
    def get_head(cls, name: str) -> Optional['Region']:
        return cls.HEADS.get(name)

# Sample usage
if __name__ == "__main__":
    r1 = Region("Planner", meta={"agent_type": "planner", "task": "loan_approval"})
    r1.observe("User requested a loan")
    r1.plan("Check credit score and income")
    r1.effect("credit_api", "score: 720")
    r1.summarize("User is eligible")

    print(r1.summary())

    r1.save_to_disk("logs")
    r1.save_to_sqlite("memento.db")

    loaded = Region.load_from_disk("logs/Planner.jsonl")
    print("Loaded from JSONL:", loaded.summary())

    loaded_sqlite = Region.load_from_sqlite("memento.db", "Planner")
    print("Loaded from SQLite:", loaded_sqlite.summary())

    r2 = r1.fork("RetryPlanner")
    r2.plan("Try with updated income")
    r2.effect("income_api", "income: 80k")
    print(r2.summary())
    print("Diff from fork:", r1.diff(r2))

    r3 = r1.fork("AlternatePlanner")
    r3.observe("User updated loan amount")
    r3.effect("loan_api", "amount: 50k")

    r_merged = r2.merge(r3, "UnifiedPlanner")
    print(r_merged.summary())
    for e in r_merged.replay():
        print("-", e["op"], e["content"])

    Region.gc(keep=["UnifiedPlanner"])
    print("Remaining heads:", list(Region.HEADS.keys()))
