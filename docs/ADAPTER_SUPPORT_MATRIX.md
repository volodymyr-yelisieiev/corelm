# Adapter Support Matrix

| Path | Classification | Strict Eligible | Notes |
|---|---|---:|---|
| `transformers_direct` | DIRECT / STRICT-BENCH ELIGIBLE | Yes | Local Hugging Face/safetensors execution through `transformers` and `torch`. Blocked until optional dependencies and local model files exist. |
| `llamacpp_direct` | DIRECT / STRICT-BENCH ELIGIBLE | Yes | Local GGUF execution through `llama-cpp-python`. Blocked until optional dependency and model path exist. |
| `deterministic_direct_smoke` | DIRECT / PARTIAL METRICS | No | In-process deterministic smoke adapter for API/UI/CLI verification. It is not a production LLM benchmark result. |
| `ollama_local_model` connector | BRIDGE / NON-STRICT | No | Uses Ollama HTTP API. Useful product bridge with provider metrics, but excluded from strict direct results. |
| `lm_studio` connector | BRIDGE / NON-STRICT | No | Uses OpenAI-compatible local HTTP API. Excluded from strict direct results. |
| `openai_compatible_llm` connector | BRIDGE / NON-STRICT | No | Remote or local provider-style API. Excluded from strict direct results. |
| Closed cloud APIs | UNSUPPORTED | No | Not direct runtime execution and cannot provide strict local determinism. |
| Closed runtimes without token trace hooks | BLOCKED BY LICENSE / CLOSED RUNTIME / MANUAL STEP | No | May be documented manually if a direct hook becomes available later. |

## Discovery

`transformers_direct` discovers local model directories from
`CORELM_TRANSFORMERS_MODEL_DIRS` and common Hugging Face cache paths.
`llamacpp_direct` discovers `.gguf` files from `CORELM_LLAMACPP_MODEL_DIRS`,
`~/models`, and common LM Studio cache paths.

## Policy

Strict mode rejects bridge connectors, adapters that are not marked strict
eligible, adapters blocked by missing optional dependencies, empty `model_ref`,
and profiles without an explicit seed.
