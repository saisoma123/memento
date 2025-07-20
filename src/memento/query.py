# memento/query.py
from typing import Callable, List, Optional
from src.memento.core import MemoryGraph, EventNode
from src.memento.region import Region

class MemoryQuery:
    def __init__(self, graph: MemoryGraph):
        self.graph = graph

    def search_text(self, text: str, start: Optional[str] = None) -> List[EventNode]:
        """Return all events containing the substring 'text'."""
        return self.graph.traverse(start=start, filter_fn=lambda e: text in e.content)

    def filter_by_op(self, op: str, start: Optional[str] = None) -> List[EventNode]:
        """Return all events with a specific operation."""
        return self.graph.traverse(start=start, filter_fn=lambda e: e.op == op)

    def filter_by_meta(self, key: str, value: str, start: Optional[str] = None) -> List[EventNode]:
        """Return all events where meta[key] == value."""
        return self.graph.traverse(start=start, filter_fn=lambda e: e.meta.get(key) == value)

    def replay_region(self, region: Region) -> List[EventNode]:
        return region.replay(self.graph)


    def summarize_region(self, region: Region) -> str:
        """Generate a summary string of a region's memory."""
        events = self.replay_region(region)
        head_str = ', '.join(h[:8] for h in region.heads)
        return f"Region '{region.name}' with {len(events)} event(s). Heads: {head_str}"


    def custom_query(self, filter_fn: Callable[[EventNode], bool], start: Optional[str] = None) -> List[EventNode]:
        """Run an arbitrary filter function over the DAG."""
        return self.graph.traverse(start=start, filter_fn=filter_fn)
