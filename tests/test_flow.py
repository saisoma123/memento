from src.memento.core import MemoryGraph
from src.memento.region import Region
from src.memento.region_store import RegionStore
import tempfile
import os

def test_flow():
    print("== Initializing ==")
    graph = MemoryGraph()

    # Add some base events directly
    eid1 = graph.add_event("observe", "User visited homepage")
    eid2 = graph.add_event("plan", "Suggest recommendations")
    eid3 = graph.add_event("effect", "recommender_api: 3 items")

    assert graph.get(eid1).op == "observe"
    assert graph.get(eid2).content == "Suggest recommendations"
    assert len(graph.heads) == 1

    print("== Region A Operations ==")
    region_a = Region(name="AgentA", meta={"role": "planner"})
    region_a.observe("User asked for a loan", graph)
    region_a.plan("Check credit score", graph)
    region_a.effect("credit_api", "score: 720", graph)
    region_a.summarize("User is eligible", graph)

    prompt_a = region_a.for_prompt(graph)
    assert "[PLAN] Check credit score" in prompt_a
    print(prompt_a)

    print("== Fork to Region B ==")
    region_b = region_a.fork("AgentB")
    region_b.plan("Try with updated income", graph)
    region_b.effect("income_api", "income: 80k", graph)

    prompt_b = region_b.for_prompt(graph)
    assert "income: 80k" in prompt_b
    print(prompt_b)

    print("== Merging to Unified ==")
    unified = region_a.merge(region_b, new_name="UnifiedAgent")
    unified.observe("User confirmed details", graph)
    unified.effect("loan_api", "amount: 50k", graph)

    prompt_u = unified.for_prompt(graph)
    assert "User confirmed details" in prompt_u
    print(prompt_u)

    print("== Diff: Unified - AgentA ==")
    diff = unified.diff(region_a, graph)
    for e in diff:
        print(f"[{e.op.upper()}] {e.content}")
    assert any("income" in e.content for e in diff)

    print("== Search & Filter ==")

    search_hits = graph.search("income")
    print("Search results for keyword 'income':")
    for e in search_hits:
        print(f"[{e.op.upper()}] {e.content}")
    assert any("income" in e.content for e in search_hits)

    effect_events = graph.find_by_op("effect")
    print("\nAll events with op 'effect':")
    for e in effect_events:
        print(f"[{e.op.upper()}] {e.content}")
    assert all(e.op == "effect" for e in effect_events)

    print("\n== Compact Replay ==")
    compacted = unified.compact(graph)
    print("Chronologically sorted compacted UnifiedAgent events:")
    for e in compacted:
        print(f"[{e.op.upper()}] {e.content}")
    assert all(isinstance(e.id, str) for e in compacted)


    print("== RegionStore Save/Load ==")
    store = RegionStore()
    store.add(region_a)
    store.add(region_b)
    store.add(unified)

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "regions.json")
        store.save_to_json(path)
        assert os.path.exists(path)

        loaded = RegionStore.load_from_json(path)
        assert "AgentA" in loaded.regions
        assert "UnifiedAgent" in loaded.regions
        assert loaded.get("AgentA").name == "AgentA"

    print("== Summary Checks ==")
    print(graph.summary())
    print(region_a.summary())
    print(store.summary())

    print("\n✅ All major functionality tested!")

if __name__ == "__main__":
    test_flow()
