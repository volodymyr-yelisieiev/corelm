from benches.runner import instantiate_systems, load_scenarios, run_one


def test_reference_outperforms_sliding_window_on_delayed_recall():
    scenarios = load_scenarios("benches/scenarios")
    scenario = next(s for s in scenarios if s["name"] == "delayed_recall_noise")
    systems = instantiate_systems()
    slide = run_one(systems["sliding_window"], scenario, seed=0)
    ref = run_one(systems["reference_kernel"], scenario, seed=0)
    assert ref["accuracy"] == 1.0
    assert slide["accuracy"] < ref["accuracy"]
