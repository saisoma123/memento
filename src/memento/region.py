import time
from typing import Optional, Dict, List
from src.memento.core import EventNode

class Region:
    def __init__(self, name: str, meta: Optional[Dict] = None):
        self.name = name
        self.meta = meta or {}
        self.heads: set[str] = set()  # head node hashes for this region

    def observe(self, content: str, graph):
        self._append_event("observe", content, graph)

    def plan(self, content: str, graph):
        self._append_event("plan", content, graph)

    def effect(self, tool: str, result: str, graph):
        self._append_event("effect", f"{tool}: {result}", graph)

    def summarize(self, content: str, graph):
        self._append_event("summarize", content, graph)

    def _append_event(self, op: str, content: str, graph):
        timestamp = time.time()
        parents = list(self.heads) or []
        eid = graph.add_event(op=op, content=content, meta=self.meta, parents=parents)
        self.heads = {eid}

    def fork(self, new_name: str) -> 'Region':
        new_region = Region(name=new_name, meta=self.meta.copy())
        new_region.heads = set(self.heads)
        return new_region

    def merge(self, other: 'Region', new_name: Optional[str] = None) -> 'Region':
        merged = Region(name=new_name or f"{self.name}_MERGED_{other.name}")
        merged.heads = self.heads.union(other.heads)
        return merged

    def replay(self, graph) -> List[EventNode]:
        return graph.traverse(start=None, filter_fn=lambda e: e.id in self._reachable_hashes(graph))

    def _reachable_hashes(self, graph) -> set:
        visited = set()
        stack = list(self.heads)
        while stack:
            h = stack.pop()
            if h in visited: continue
            visited.add(h)
            node = graph.get(h)
            if node:
                stack.extend(node.parents)
        return visited

    def diff(self, other: 'Region', graph) -> List[EventNode]:
      self_events = {e.id: e for e in self.replay(graph)}
      other_events = {e.id: e for e in other.replay(graph)}
      diff_ids = set(self_events.keys()) - set(other_events.keys())
      return sorted([self_events[i] for i in diff_ids], key=lambda e: e.timestamp)


    def compact(self, graph) -> List[EventNode]:
        """Returns a deduplicated, chronologically sorted set of reachable events."""
        nodes = self.replay(graph)
        seen = set()
        result = []
        for node in sorted(nodes, key=lambda n: n.timestamp):
            if node.id not in seen:
                result.append(node)
                seen.add(node.id)
        return result

    def for_prompt(self, graph) -> str:
        """Formats region memory into a readable prompt string."""
        events = self.compact(graph)
        return "\n".join(f"[{e.op.upper()}] {e.content}" for e in events)

    def to_dict(self):
        return {
            "name": self.name,
            "meta": self.meta,
            "heads": list(self.heads)
        }

    @staticmethod
    def from_dict(d: Dict) -> 'Region':
        region = Region(name=d["name"], meta=d.get("meta", {}))
        region.heads = set(d.get("heads", []))
        return region

    def summary(self) -> str:
        return f"Region '{self.name}'\n - Heads: {[h[:8] for h in self.heads]}\n - Meta: {self.meta}"
