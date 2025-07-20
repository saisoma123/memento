from src.memento.core import MemoryGraph
from src.memento.region import Region
from src.memento.query import MemoryQuery

def test_query():
    print("== MemoryQuery Tests ==")
    
    graph = MemoryGraph()

    # Create a region and add events
    region = Region("AgentX", meta={"agent": "analyzer"})
    region.observe("User logged in", graph)
    region.plan("Run identity verification", graph)
    region.effect("id_api", "status: verified", graph)
    region.summarize("User identity confirmed", graph)

    # Instantiate the MemoryQuery object
    mq = MemoryQuery(graph)

    print("-- search_text('User') --")
    hits = mq.search_text("User")
    for e in hits:
        print(f"[{e.op.upper()}] {e.content}")
    assert len(hits) == 2  # User appears in "User logged in" and "User identity confirmed"

    print("\n-- filter_by_op('plan') --")
    plan_events = mq.filter_by_op("plan")
    for e in plan_events:
        print(f"[{e.op.upper()}] {e.content}")
    assert len(plan_events) == 1
    assert plan_events[0].content == "Run identity verification"

    print("\n-- filter_by_meta('agent', 'analyzer') --")
    meta_hits = mq.filter_by_meta("agent", "analyzer")
    for e in meta_hits:
        print(f"[{e.op.upper()}] {e.content} (meta: {e.meta})")
    assert len(meta_hits) == 4  # all 4 events share same meta

    print("\n-- replay_region(region) --")
    replay = mq.replay_region(region)
    for e in replay:
        print(f"[{e.op.upper()}] {e.content}")
    assert replay[-1].op == "summarize"

    print("\n-- summarize_region(region) --")
    summary = mq.summarize_region(region)
    print(summary)
    assert f"Region '{region.name}'" in summary

    print("\n-- custom_query(lambda e: 'verified' in e.content) --")
    custom_hits = mq.custom_query(lambda e: "verified" in e.content)
    for e in custom_hits:
        print(f"[{e.op.upper()}] {e.content}")
    assert len(custom_hits) == 1
    assert custom_hits[0].content == "id_api: status: verified"

    print("\n✅ All MemoryQuery methods tested successfully!")

if __name__ == "__main__":
    test_query()
