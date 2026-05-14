# Windows Direct Benchmark Build

The Windows build remains the Electron desktop plus Python sidecar package. The
direct benchmark build adds direct runtime and benchmark modules to the existing
bundled `services` tree.

Build command:

```powershell
npm run desktop:package:win
```

The package includes the direct benchmark API, CLI module, profile persistence,
Benchmark Studio UI, and report export code. It does not bundle model weights,
Transformers, PyTorch, llama.cpp binaries, or GGUF/checkpoint files. Strict live
runtime runs on Windows require the user to install compatible optional runtime
dependencies and point the profile at local model files.

If optional dependencies or model files are missing, strict runs are marked
blocked and no placeholder strict report is produced.
