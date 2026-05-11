from benches.scenario_loader import load_scenarios
from corelm.reference_kernel import ReferenceKernel


def test_reference_replay_is_deterministic():
    scenarios = load_scenarios("benches/scenarios")
    ref = ReferenceKernel()
    scenario = next(s for s in scenarios if s["name"] == "full_spec_trace")
    out1 = ref.replay(scenario["events"], scenario["queries"], seed=0)
    out2 = ref.replay(scenario["events"], scenario["queries"], seed=0)
    assert out1 == out2


def test_reference_has_no_invariant_violations():
    scenarios = load_scenarios("benches/scenarios")
    ref = ReferenceKernel()
    for scenario in scenarios:
        ref.reset(seed=0)
        for event in scenario["events"]:
            ref.step(event)
        assert ref.stats()["invariant_violations"] == 0, scenario["name"]
