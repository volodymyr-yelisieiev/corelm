from benches.scenario_loader import load_scenarios
from corelm.oracle_kernel import OracleKernel
from corelm.reference_kernel import ReferenceKernel


def test_reference_matches_oracle_on_all_queries():
    scenarios = load_scenarios("benches/scenarios")
    oracle = OracleKernel()
    ref = ReferenceKernel()
    for scenario in scenarios:
        oracle.reset(seed=0)
        ref.reset(seed=0)
        for event in scenario["events"]:
            oracle.step(event)
            ref.step(event)
        for query in scenario["queries"]:
            assert ref.answer(query) == oracle.answer(query), (scenario["name"], query.query_id)
