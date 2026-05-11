# Core LM Publication Benchmark Report

Generated systems: sliding_window, large_context_window, periodic_summary, retrieval_only, oracle_core, reference_kernel

## Summary

| System | Passed | Accuracy | Determinism | Provenance | Violations | Max Norm | Facts | Memory Words |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| sliding_window | 10/18 | 0.639 | 1.000 | 0.000 | 0.000 | 0.000 | 49 | 989 |
| large_context_window | 13/18 | 0.833 | 1.000 | 0.000 | 0.000 | 0.000 | 62 | 2379 |
| periodic_summary | 14/18 | 0.861 | 1.000 | 0.000 | 0.000 | 0.000 | 61 | 174 |
| retrieval_only | 13/18 | 0.806 | 1.000 | 0.000 | 0.000 | 0.000 | 63 | 2962 |
| oracle_core | 18/18 | 1.000 | 1.000 | 1.000 | 0.000 | 9.354 | 58 | 2962 |
| reference_kernel | 18/18 | 1.000 | 1.000 | 1.000 | 0.000 | 9.354 | 58 | 2962 |

## Scenario results

### adversarial_mixed_branch

| System | Accuracy | Passed | Determinism | Provenance | Violations |
|---|---:|---:|---:|---:|---:|
| sliding_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| large_context_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| periodic_summary | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| retrieval_only | 0.500 | no | 1.000 | 0.000 | 0.000 |
| oracle_core | 1.000 | yes | 1.000 | 1.000 | 0.000 |
| reference_kernel | 1.000 | yes | 1.000 | 1.000 | 0.000 |

### benchmark_principles

| System | Accuracy | Passed | Determinism | Provenance | Violations |
|---|---:|---:|---:|---:|---:|
| sliding_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| large_context_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| periodic_summary | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| retrieval_only | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| oracle_core | 1.000 | yes | 1.000 | 1.000 | 0.000 |
| reference_kernel | 1.000 | yes | 1.000 | 1.000 | 0.000 |

### branch_isolation_core_infra_publication

| System | Accuracy | Passed | Determinism | Provenance | Violations |
|---|---:|---:|---:|---:|---:|
| sliding_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| large_context_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| periodic_summary | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| retrieval_only | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| oracle_core | 1.000 | yes | 1.000 | 1.000 | 0.000 |
| reference_kernel | 1.000 | yes | 1.000 | 1.000 | 0.000 |

### canonical_pipeline

| System | Accuracy | Passed | Determinism | Provenance | Violations |
|---|---:|---:|---:|---:|---:|
| sliding_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| large_context_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| periodic_summary | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| retrieval_only | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| oracle_core | 1.000 | yes | 1.000 | 1.000 | 0.000 |
| reference_kernel | 1.000 | yes | 1.000 | 1.000 | 0.000 |

### chained_corrections

| System | Accuracy | Passed | Determinism | Provenance | Violations |
|---|---:|---:|---:|---:|---:|
| sliding_window | 0.500 | no | 1.000 | 0.000 | 0.000 |
| large_context_window | 0.500 | no | 1.000 | 0.000 | 0.000 |
| periodic_summary | 0.500 | no | 1.000 | 0.000 | 0.000 |
| retrieval_only | 0.500 | no | 1.000 | 0.000 | 0.000 |
| oracle_core | 1.000 | yes | 1.000 | 1.000 | 0.000 |
| reference_kernel | 1.000 | yes | 1.000 | 1.000 | 0.000 |

### contradiction_api_port

| System | Accuracy | Passed | Determinism | Provenance | Violations |
|---|---:|---:|---:|---:|---:|
| sliding_window | 0.500 | no | 1.000 | 0.000 | 0.000 |
| large_context_window | 0.500 | no | 1.000 | 0.000 | 0.000 |
| periodic_summary | 0.500 | no | 1.000 | 0.000 | 0.000 |
| retrieval_only | 0.000 | no | 1.000 | 0.000 | 0.000 |
| oracle_core | 1.000 | yes | 1.000 | 1.000 | 0.000 |
| reference_kernel | 1.000 | yes | 1.000 | 1.000 | 0.000 |

### contradiction_rename

| System | Accuracy | Passed | Determinism | Provenance | Violations |
|---|---:|---:|---:|---:|---:|
| sliding_window | 0.500 | no | 1.000 | 0.000 | 0.000 |
| large_context_window | 0.500 | no | 1.000 | 0.000 | 0.000 |
| periodic_summary | 0.500 | no | 1.000 | 0.000 | 0.000 |
| retrieval_only | 0.500 | no | 1.000 | 0.000 | 0.000 |
| oracle_core | 1.000 | yes | 1.000 | 1.000 | 0.000 |
| reference_kernel | 1.000 | yes | 1.000 | 1.000 | 0.000 |

### delayed_recall_noise

| System | Accuracy | Passed | Determinism | Provenance | Violations |
|---|---:|---:|---:|---:|---:|
| sliding_window | 0.000 | no | 1.000 | 0.000 | 0.000 |
| large_context_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| periodic_summary | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| retrieval_only | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| oracle_core | 1.000 | yes | 1.000 | 1.000 | 0.000 |
| reference_kernel | 1.000 | yes | 1.000 | 1.000 | 0.000 |

### full_spec_trace

| System | Accuracy | Passed | Determinism | Provenance | Violations |
|---|---:|---:|---:|---:|---:|
| sliding_window | 0.000 | no | 1.000 | 0.000 | 0.000 |
| large_context_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| periodic_summary | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| retrieval_only | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| oracle_core | 1.000 | yes | 1.000 | 1.000 | 0.000 |
| reference_kernel | 1.000 | yes | 1.000 | 1.000 | 0.000 |

### long_horizon_publication_plan

| System | Accuracy | Passed | Determinism | Provenance | Violations |
|---|---:|---:|---:|---:|---:|
| sliding_window | 0.000 | no | 1.000 | 0.000 | 0.000 |
| large_context_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| periodic_summary | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| retrieval_only | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| oracle_core | 1.000 | yes | 1.000 | 1.000 | 0.000 |
| reference_kernel | 1.000 | yes | 1.000 | 1.000 | 0.000 |

### near_duplicate_paraphrase_pack

| System | Accuracy | Passed | Determinism | Provenance | Violations |
|---|---:|---:|---:|---:|---:|
| sliding_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| large_context_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| periodic_summary | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| retrieval_only | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| oracle_core | 1.000 | yes | 1.000 | 1.000 | 0.000 |
| reference_kernel | 1.000 | yes | 1.000 | 1.000 | 0.000 |

### noise_saturation

| System | Accuracy | Passed | Determinism | Provenance | Violations |
|---|---:|---:|---:|---:|---:|
| sliding_window | 0.000 | no | 1.000 | 0.000 | 0.000 |
| large_context_window | 0.500 | no | 1.000 | 0.000 | 0.000 |
| periodic_summary | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| retrieval_only | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| oracle_core | 1.000 | yes | 1.000 | 1.000 | 0.000 |
| reference_kernel | 1.000 | yes | 1.000 | 1.000 | 0.000 |

### orchestrator_invariants

| System | Accuracy | Passed | Determinism | Provenance | Violations |
|---|---:|---:|---:|---:|---:|
| sliding_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| large_context_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| periodic_summary | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| retrieval_only | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| oracle_core | 1.000 | yes | 1.000 | 1.000 | 0.000 |
| reference_kernel | 1.000 | yes | 1.000 | 1.000 | 0.000 |

### perturbation_classes

| System | Accuracy | Passed | Determinism | Provenance | Violations |
|---|---:|---:|---:|---:|---:|
| sliding_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| large_context_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| periodic_summary | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| retrieval_only | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| oracle_core | 1.000 | yes | 1.000 | 1.000 | 0.000 |
| reference_kernel | 1.000 | yes | 1.000 | 1.000 | 0.000 |

### provenance_trace

| System | Accuracy | Passed | Determinism | Provenance | Violations |
|---|---:|---:|---:|---:|---:|
| sliding_window | 0.000 | no | 1.000 | 0.000 | 0.000 |
| large_context_window | 0.000 | no | 1.000 | 0.000 | 0.000 |
| periodic_summary | 0.000 | no | 1.000 | 0.000 | 0.000 |
| retrieval_only | 0.000 | no | 1.000 | 0.000 | 0.000 |
| oracle_core | 1.000 | yes | 1.000 | 1.000 | 0.000 |
| reference_kernel | 1.000 | yes | 1.000 | 1.000 | 0.000 |

### rename_rebuild_trace

| System | Accuracy | Passed | Determinism | Provenance | Violations |
|---|---:|---:|---:|---:|---:|
| sliding_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| large_context_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| periodic_summary | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| retrieval_only | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| oracle_core | 1.000 | yes | 1.000 | 1.000 | 0.000 |
| reference_kernel | 1.000 | yes | 1.000 | 1.000 | 0.000 |

### repetition_paraphrase_llm_role

| System | Accuracy | Passed | Determinism | Provenance | Violations |
|---|---:|---:|---:|---:|---:|
| sliding_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| large_context_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| periodic_summary | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| retrieval_only | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| oracle_core | 1.000 | yes | 1.000 | 1.000 | 0.000 |
| reference_kernel | 1.000 | yes | 1.000 | 1.000 | 0.000 |

### state_space_foundation

| System | Accuracy | Passed | Determinism | Provenance | Violations |
|---|---:|---:|---:|---:|---:|
| sliding_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| large_context_window | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| periodic_summary | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| retrieval_only | 1.000 | yes | 1.000 | 0.000 | 0.000 |
| oracle_core | 1.000 | yes | 1.000 | 1.000 | 0.000 |
| reference_kernel | 1.000 | yes | 1.000 | 1.000 | 0.000 |
