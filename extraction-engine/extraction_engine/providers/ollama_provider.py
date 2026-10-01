"""Local Ollama vision provider (default local model: qwen2.5vl:7b).

Talks to a local Ollama server over HTTP. Fully local — no cloud, no key.
Lazy imports keep the file importable even if httpx is absent.
"""
from __future__ import annotations

import base64
from pathlib import Path

from extraction_engine.parsing import result_from_json
from extraction_engine.prompts import EXTRACTION_INSTRUCTIONS, EXTRACTION_SYSTEM
from extraction_engine.providers.base import (
    ExtractionError,
    ExtractionProvider,
    ProviderUnavailable,
)
from extraction_engine.schema import ExtractionResult


class OllamaProvider(ExtractionProvider):
    name = "ollama"

    def _host(self) -> str:
        return self.options.get("host", "http://localhost:11434").rstrip("/")

    def is_available(self) -> bool:
        try:
            import httpx
        except Exception:
            return False
        try:
            resp = httpx.get(f"{self._host()}/api/tags", timeout=3)
            if resp.status_code != 200:
                return False
            model = self.options.get("model", "qwen2.5vl:7b")
            names = [m.get("name", "") for m in resp.json().get("models", [])]
            # Match with or without an explicit :tag.
            return any(n == model or n.split(":")[0] == model.split(":")[0] for n in names)
        except Exception:
            return False

    def extract(self, file_path: Path) -> ExtractionResult:
        import httpx

        model = self.options.get("model", "qwen2.5vl:7b")
        timeout = float(self.options.get("timeout_seconds", 300))
        b64 = base64.b64encode(file_path.read_bytes()).decode()

        payload = {
            "model": model,
            "prompt": EXTRACTION_INSTRUCTIONS,
            "system": EXTRACTION_SYSTEM,
            "images": [b64],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }
        try:
            resp = httpx.post(f"{self._host()}/api/generate", json=payload, timeout=timeout)
            resp.raise_for_status()
            content = resp.json().get("response", "")
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"Ollama request failed: {exc}") from exc

        try:
            return result_from_json(content, provider=self.name, model=model)
        except Exception as exc:
            raise ExtractionError(f"Could not parse Ollama output as JSON: {exc}") from exc
