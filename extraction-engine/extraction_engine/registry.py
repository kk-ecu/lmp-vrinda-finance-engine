"""Defensive provider registry.

Each provider is imported in isolation. If a provider module is missing (file
deleted) or fails to import, it is simply skipped with a recorded reason — the
other providers and the whole application keep working. This is what makes any
of the four providers independently deletable.
"""
from __future__ import annotations

import importlib
from typing import Callable

from extraction_engine.providers.base import ExtractionProvider, ProviderUnavailable

# Map provider name -> (module path, class name). Add/remove entries freely;
# deleting a provider's file simply makes it unavailable, not fatal.
# Product providers: openrouter (cloud) and ollama (local). 'stub' is retained
# for offline tests only (not a product provider). Deleting a provider's file
# simply makes it unavailable here — never fatal.
_PROVIDER_SPECS: dict[str, tuple[str, str]] = {
    "openrouter": ("extraction_engine.providers.openrouter_provider", "OpenRouterProvider"),
    "ollama": ("extraction_engine.providers.ollama_provider", "OllamaProvider"),
    "stub": ("extraction_engine.providers.stub_provider", "StubProvider"),
}

# Reasons a provider could not be loaded (name -> message), for diagnostics.
load_errors: dict[str, str] = {}


def available_provider_names() -> list[str]:
    """Provider names whose module can be imported in this environment."""
    names = []
    for name in _PROVIDER_SPECS:
        if _load_class(name) is not None:
            names.append(name)
    return names


def _load_class(name: str) -> Callable[..., ExtractionProvider] | None:
    spec = _PROVIDER_SPECS.get(name)
    if spec is None:
        return None
    module_path, class_name = spec
    try:
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except Exception as exc:  # ImportError, AttributeError, etc.
        load_errors[name] = f"{type(exc).__name__}: {exc}"
        return None


def create_provider(name: str, options: dict | None = None) -> ExtractionProvider:
    cls = _load_class(name)
    if cls is None:
        reason = load_errors.get(name, "not registered")
        raise ProviderUnavailable(f"Provider '{name}' could not be loaded ({reason}).")
    return cls(options or {})
