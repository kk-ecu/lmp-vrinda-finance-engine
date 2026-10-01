"""Public facade for the extraction engine.

Typical use:
    from extraction_engine import extract_from_file, load_config
    cfg = load_config()
    result = extract_from_file(path, cfg)
"""
from __future__ import annotations

from pathlib import Path

from extraction_engine.config import ExtractionConfig, load_config
from extraction_engine.providers.base import (
    ExtractionError,
    ExtractionProvider,
    ProviderUnavailable,
)
from extraction_engine.registry import (
    available_provider_names,
    create_provider,
    load_errors,
)
from extraction_engine.schema import ExtractedRow, ExtractionResult

__all__ = [
    "ExtractionConfig",
    "ExtractionError",
    "ExtractionProvider",
    "ExtractionResult",
    "ExtractedRow",
    "ProviderUnavailable",
    "available_provider_names",
    "create_provider",
    "extract_from_file",
    "get_provider",
    "load_config",
    "load_errors",
]


def get_provider(config: ExtractionConfig | None = None) -> ExtractionProvider:
    config = config or load_config()
    return create_provider(config.provider, config.provider_options())


def extract_from_file(
    file_path: str | Path, config: ExtractionConfig | None = None
) -> ExtractionResult:
    """Run the configured provider against a single source file."""
    config = config or load_config()
    provider = get_provider(config)
    if not provider.is_available():
        raise ProviderUnavailable(
            f"Provider '{config.provider}' is configured but not available "
            f"(missing dependency, binary, or API key)."
        )
    return provider.extract(Path(file_path))
