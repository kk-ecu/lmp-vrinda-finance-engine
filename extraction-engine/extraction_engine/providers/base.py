"""Provider interface and shared errors.

A provider converts a source file into an ExtractionResult. Optional third-party
dependencies MUST be imported lazily inside methods (never at module top) so a
provider file remains importable even when its dependency is absent — this is
what makes each provider independently deletable/optional.
"""
from __future__ import annotations

import abc
from pathlib import Path
from typing import Any

from extraction_engine.schema import ExtractionResult


class ExtractionError(RuntimeError):
    """Raised when extraction cannot be performed."""


class ProviderUnavailable(ExtractionError):
    """Raised when a provider's dependency, binary, or key is missing."""


class ExtractionProvider(abc.ABC):
    name: str = "base"

    def __init__(self, options: dict[str, Any] | None = None):
        self.options = options or {}

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Return True if this provider can run (deps/keys/binaries present)."""

    @abc.abstractmethod
    def extract(self, file_path: Path) -> ExtractionResult:
        """Extract structured rows from a single source file."""
