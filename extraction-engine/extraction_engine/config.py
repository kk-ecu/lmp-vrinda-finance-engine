"""Load and represent extraction-engine configuration from config.yaml.

Environment variables can override the selected provider:
    EXTRACTION_PROVIDER=ollama
    EXTRACTION_LOW_CONFIDENCE_THRESHOLD=0.7
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_ENGINE_DIR = Path(__file__).resolve().parents[1]  # extraction-engine/
_DEFAULT_CONFIG_PATH = _ENGINE_DIR / "config.yaml"


@dataclass
class ExtractionConfig:
    provider: str = "stub"
    low_confidence_threshold: float = 0.80
    providers: dict[str, dict[str, Any]] = field(default_factory=dict)

    def provider_options(self, name: str | None = None) -> dict[str, Any]:
        return dict(self.providers.get(name or self.provider, {}) or {})


def load_config(path: str | Path | None = None) -> ExtractionConfig:
    config_path = Path(path) if path else _DEFAULT_CONFIG_PATH
    data: dict[str, Any] = {}
    if config_path.exists():
        loaded = yaml.safe_load(config_path.read_text()) or {}
        data = loaded.get("extraction", {}) or {}

    provider = os.getenv("EXTRACTION_PROVIDER", data.get("provider", "stub"))
    threshold = float(
        os.getenv(
            "EXTRACTION_LOW_CONFIDENCE_THRESHOLD",
            data.get("low_confidence_threshold", 0.80),
        )
    )
    return ExtractionConfig(
        provider=provider,
        low_confidence_threshold=threshold,
        providers=data.get("providers", {}) or {},
    )
