# I2 evidence

Reproducibility bundles from real `lemonade-fusion` (I2) runs — one natural-language
request driven through Pi -> Lemonade/Qwen -> guided MCP -> Fusion, plus one invalid
request that must fail safely.

Generate a bundle with:

```powershell
./pi/run-i2-evidence.ps1
```

Each run writes `i2-evidence/<timestamp>/` containing `metadata.json` (commit,
Pi/Lemonade versions, model, backend, GPU, driver, temperature), `doctor.txt`,
`lemonade.txt`, `success.jsonl` and `fail_safely.jsonl` (Pi JSON event streams),
`exports.txt`, and `run.md` (summary + reviewer checklist).

Commit the bundles you want to keep as the milestone's acceptance evidence. This is
the record the ROADMAP "Acceptance test" calls for; it does **not** replace the
server contract regression suite (`evaluations/`), which tests server behavior, not
model behavior.
