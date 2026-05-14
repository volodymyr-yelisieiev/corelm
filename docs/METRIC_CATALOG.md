# Metric Catalog

All benchmark metrics are persisted as JSON with source semantics. Missing
runtime fields remain `null`; unavailable metrics are never fabricated.

## Runtime / Engine

- `runtime_family`, `runtime_version`, `adapter_id`
- `model_id`, `model_path_or_ref`, `quantization`, `precision`
- `backend`, `device`, `threads`, `batch_size`, `n_ctx`, `n_predict`
- `actual_generated_token_count`, `prompt_token_count`, `total_token_count`
- `load_ms`, `warmup_ms`, `ttft_ms`, `total_ms`, `prompt_eval_ms`, `decode_ms`
- `prompt_tps`, `decode_tps`, `end_to_end_tps`
- `peak_ram_mb`, `avg_ram_mb`, `peak_vram_mb`, `avg_vram_mb`
- `prompt_hash`, `system_hash`, `generation_config_hash`,
  `adapter_config_hash`, `build_hash`

## Determinism

- `exact_output_repeat_rate`
- `exact_token_sequence_repeat_rate`
- `prefix_stability_at_1`, `prefix_stability_at_5`, `prefix_stability_at_10`
- `output_hash_repeat_rate`
- `token_trace_hash_repeat_rate`
- `sampler_config_match_rate`
- `run_manifest_match_rate`
- `logit_trace_divergence`, `topk_candidate_divergence`
- `entropy_trace_l2`, `confidence_trace_l2`
- `restart_reproducibility_rate`
- `state_replay_consistency_score`
- `direct_runtime_determinism_score`
- `end_to_end_determinism_score`

## Compression

- `raw_char_count`, `raw_byte_count`, `raw_token_count`
- `canonical_char_count`, `canonical_byte_count`, `canonical_token_count`
- `compressed_state_byte_count`, `compressed_history_byte_count`
- `void_token_count`
- `duplicate_items_removed`
- `contradiction_candidates_found`, `contradiction_candidates_resolved`
- `schema_fields_extracted`, `key_value_pairs_extracted`
- `digest_stability`, `canonicalization_applied`
- `raw_to_canonical_ratio`, `canonical_to_state_ratio`
- `overall_compression_ratio`
- `compression_latency_ms`
- `compression_throughput_chars_per_sec`
- `compression_throughput_tokens_per_sec`
- `retention_after_compression_exact_match`
- `retention_after_compression_keyword_coverage`
- `reconstruction_error`
- `state_compression_ratio`, `history_compression_ratio`

## Core LM State

- `source_input_norm`, `state_norm`, `drift`
- `invariant_violation_rate`
- `determinism_score`, `replay_consistency_score`
- `stability_proxy`, `energy`, `energy_drift`, `csi`
- `response_variance_index`, `spectral_radius`, `lyapunov_proxy` when present
- `branch_contamination_rate`
- `supersession_accuracy`
- `provenance_coverage`
- `commit_accept_rate`
- `rollback_or_reject_rate`

## Output / Quality

- `exact_match`, `normalized_match`, `fuzzy_match`
- `keyword_coverage`
- `format_compliance`
- `json_parse_valid`, `yaml_parse_valid`, `schema_valid`
- `required_key_coverage`
- `nonempty_output`
- `repetition_ratio`
- `contradiction_flag_count`
- `packet_validity`
- `outbound_delivery_success`

## Workflow / Product

- `workflow_node_success_rate`
- `end_to_end_pipeline_success`
- `chat_publish_success`
- `ledger_commit_success`
- `replay_snapshot_success`
- `provenance_link_success`
- `report_export_success`
- `benchmark_profile_repeatability`
