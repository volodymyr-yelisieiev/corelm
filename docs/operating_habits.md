# Operating habits for keeping local results at 100%

These are process rules, not code changes.

1. **Always ingest structured facts.** Use explicit `branch`, `subject`, `attribute`, and `value` fields whenever possible.
2. **Use corrections for changes.** Do not overwrite a conflicting fact with a new plain fact. Use `correct` so supersession and provenance remain intact.
3. **Keep branches narrow.** Separate architecture, operations, publication, and sales claims into different branches.
4. **Freeze benchmark traces before release.** Do not adjust scenarios after seeing benchmark outcomes.
5. **Run the local verification bundle before every handoff.** Execute `make release-check` or `bash tools/validate_local_variants.sh`.
6. **Treat LLM text as excitation, not truth.** Durable claims should enter through the structured ingest/correct path.
7. **Package from a clean tree only.** Remove build caches, wheel output, and temporary session artifacts before cutting a release zip.
