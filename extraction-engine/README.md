# Extraction Engine

Self-contained, provider-pluggable handwriting/document extraction for the
LMP Vrinda Finance Engine.

Given a source image/PDF, a provider returns structured receipt and payment
rows, each with a **confidence** score. The application never trusts these
blindly: low-confidence rows are flagged for review and every user edit is
recorded as an audited correction (ADR-006).

## Choosing a provider

Edit `config.yaml` — a one-line change, no code edits:

```yaml
extraction:
  provider: openrouter        # fallback; app sets it from APP_ENV via EXTRACTION_PROVIDER
  low_confidence_threshold: 0.80
```

The application sets the provider from the environment (DEV→ollama, PROD→openrouter)
via the `EXTRACTION_PROVIDER` env var, which overrides `config.yaml`.

## Providers

Two **product** providers; `stub` is **test-only**.

| Provider | Local? | Cost | Handwriting | Role |
|----------|--------|------|-------------|------|
| `openrouter` | No (cloud) | ~₹0.31/month | Excellent | **PROD** default & only allowed; needs `OPENROUTER_API_KEY`. |
| `ollama` | Yes | Free | Good–Very good | **DEV** default; needs Ollama + `qwen2.5vl:7b` (~6 GB). |
| `stub` | Yes | Free | N/A (fixed data) | **Test-only**; deterministic, forced via `EXTRACTION_PROVIDER=stub`. |

## Deletability

Each provider lives in its own file under `providers/` and imports its optional
dependency **lazily** (inside the method, not at module top). The registry loads
providers defensively: if a provider file is removed or its dependency is not
installed, the others still work and the application still runs. Deleting a
provider you don't want is safe — remove its file and (optionally) its entry
from `config.yaml`.

## Public API

```python
from extraction_engine import extract_from_file, load_config

config = load_config()                      # reads config.yaml (+ env overrides)
result = extract_from_file(path, config)    # -> ExtractionResult(receipts, payments)
```

`ExtractionResult` carries `provider`, `model`, and lists of `ExtractedRow`
(each with `confidence` and `needs_review`).
