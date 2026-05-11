from benches.scenario_loader import load_scenarios
from corelm.reference_kernel import ReferenceKernel


def test_reference_dedupes_paraphrases():
    scenarios = load_scenarios("benches/scenarios")
    scenario = next(s for s in scenarios if s["name"] == "repetition_paraphrase_llm_role")
    ref = ReferenceKernel()
    ref.reset(seed=0)
    for event in scenario["events"]:
        ref.step(event)
    stats = ref.stats()
    assert stats["current_facts"] == 1
    assert stats["deduped_events"] >= 2


def test_reference_tracks_supersession():
    scenarios = load_scenarios("benches/scenarios")
    scenario = next(s for s in scenarios if s["name"] == "contradiction_api_port")
    ref = ReferenceKernel()
    ref.reset(seed=0)
    for event in scenario["events"]:
        ref.step(event)
    query = scenario["queries"][1]
    assert ref.answer(query) == "8080 -> 9090"
