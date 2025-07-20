import hashlib
import json
import time
from typing import List, Dict, Optional, Callable
from collections import defaultdict
from dataclasses import dataclass, field

def hash_event(content: dict, parents: List[str]) -> str:
    event_data = {
        "content": content,
        "parents": sorted(parents)
    }
    return hashlib.blake2b(json.dumps(event_data, sort_keys=True).encode(), digest_size=8).hexdigest()

@dataclass
class EventNode:
    op: str
    content: str
    timestamp: float
    meta: Dict
    parents: List[str]
    id: str = field(init=False)

    def __post_init__(self):
        self.id = hash_event({
            "op": self.op,
            "content": self.content,
            "timestamp": self.timestamp,
            "meta": self.meta
        }, self.parents)

class MemoryGraph:
    def __init__(self):
        self.nodes: Dict[str, EventNode] = {}
        self.children: Dict[str, List[str]] = defaultdict(list)
        self.heads: set[str] = set()

    def add_event(self, op: str, content: str, meta: Dict = {}, parents: Optional[List[str]] = None) -> str:
        timestamp = time.time()
        parents = parents if parents is not None else list(self.heads) or []
        event = EventNode(op=op, content=content, timestamp=timestamp, meta=meta, parents=parents)

        if event.id in self.nodes:
            return event.id  # Already exists

        self.nodes[event.id] = event

        for p in parents:
            self.children[p].append(event.id)

        self.heads.difference_update(parents)
        self.heads.add(event.id)

        return event.id

    def get(self, eid: str) -> Optional[EventNode]:
        return self.nodes.get(eid)

    def traverse(self, start: Optional[str] = None, filter_fn: Optional[Callable[[EventNode], bool]] = None) -> List[EventNode]:
        visited = set()
        result = []
        stack = [start] if start else list(self.heads)

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            node = self.nodes.get(current)
            if node is None:
                continue
            visited.add(current)
            if filter_fn is None or filter_fn(node):
                result.append(node)
            stack.extend(node.parents)

        return sorted(result, key=lambda e: e.timestamp)

    def find_by_op(self, op: str) -> List[EventNode]:
        return [n for n in self.nodes.values() if n.op == op]

    def search(self, keyword: str) -> List[EventNode]:
        return [n for n in self.nodes.values() if keyword in n.content]

    def summary(self) -> str:
        return f"{len(self.nodes)} events across {len(self.heads)} head(s). Heads: {[h[:8] for h in self.heads]}"
