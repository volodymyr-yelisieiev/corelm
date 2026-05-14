# Runtime Telemetry

Direct runtime adapters persist runtime telemetry per trial and summarize it per
run. Supported fields include load, warmup, TTFT, total latency, decode latency,
token counts, throughput, RAM, VRAM, backend/device/thread configuration, model
identity, precision, quantization, seed, and sampler config.

Telemetry source rules:

- direct runtime fields come from the adapter implementation;
- local timing comes from local instrumentation;
- Core LM state and compression metrics come from the sidecar path;
- unavailable backend fields remain `null`;
- bridge/provider metrics remain labeled bridge mode and are not strict direct
  telemetry.
