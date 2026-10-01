"""OpenRouter cloud vision-LLM provider (default).

Sends the source image to a multimodal model (default: google/gemini-2.5-flash)
and parses structured JSON. Requires OPENROUTER_API_KEY in the environment.
All heavy/optional imports are lazy so this file stays importable without them.
"""
from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path

from extraction_engine.parsing import result_from_json
from extraction_engine.prompts import EXTRACTION_INSTRUCTIONS, EXTRACTION_SYSTEM
from extraction_engine.providers.base import (
    ExtractionError,
    ExtractionProvider,
    ProviderUnavailable,
)
from extraction_engine.schema import ExtractionResult

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


class OpenRouterProvider(ExtractionProvider):
    name = "openrouter"

    def _api_key(self) -> str | None:
        return os.getenv(self.options.get("api_key_env", "OPENROUTER_API_KEY"))

    def is_available(self) -> bool:
        try:
            import httpx  # noqa: F401
        except Exception:
            return False
        return bool(self._api_key())

    def _verify_setting(self):
        """Resolve TLS verification. Returns an SSL context, a CA-bundle path, or bool.

        Priority (handles corporate proxies that inject a self-signed root):
          1. verify_ssl: false (or OPENROUTER_VERIFY_SSL=false) -> disable (last resort)
          2. explicit ca_bundle option / OPENROUTER_CA_BUNDLE / SSL_CERT_FILE env
          3. truststore (uses the OS trust store incl. macOS Keychain corporate roots)
          4. default True
        """
        import os

        if self.options.get("verify_ssl") is False or os.getenv("OPENROUTER_VERIFY_SSL", "").lower() == "false":
            return False

        ca = self.options.get("ca_bundle") or os.getenv("OPENROUTER_CA_BUNDLE") or os.getenv("SSL_CERT_FILE")
        if ca and Path(ca).exists():
            return ca

        # Prefer the OS trust store, which includes corporate roots on macOS/Windows.
        try:
            import ssl

            import truststore

            return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        except Exception:
            return True

    def extract(self, file_path: Path) -> ExtractionResult:
        import httpx

        api_key = self._api_key()
        if not api_key:
            raise ProviderUnavailable("OPENROUTER_API_KEY is not set.")

        if file_path.suffix.lower() not in _IMAGE_EXTS:
            raise ExtractionError(
                f"OpenRouter provider handles images; got {file_path.suffix}. "
                "Convert PDFs to images upstream or use a different provider."
            )

        mime = mimetypes.guess_type(str(file_path))[0] or "image/jpeg"
        b64 = base64.b64encode(file_path.read_bytes()).decode()
        data_url = f"data:{mime};base64,{b64}"

        model = self.options.get("model", "google/gemini-2.5-flash")
        base_url = self.options.get("base_url", "https://openrouter.ai/api/v1")
        timeout = float(self.options.get("timeout_seconds", 120))

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": EXTRACTION_SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": EXTRACTION_INSTRUCTIONS},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            "temperature": 0,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "http://localhost",
            "X-Title": "LMP Vrinda Finance Engine",
        }

        try:
            resp = httpx.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=timeout,
                verify=self._verify_setting(),
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
        except httpx.HTTPError as exc:
            hint = ""
            if "CERTIFICATE_VERIFY_FAILED" in str(exc):
                hint = (
                    " — TLS verification failed, likely a corporate proxy. Set "
                    "ca_bundle in config.yaml (e.g. /etc/ssl/cert.pem) or env "
                    "OPENROUTER_CA_BUNDLE, or verify_ssl: false as a last resort."
                )
            raise ExtractionError(f"OpenRouter request failed: {exc}{hint}") from exc

        try:
            return result_from_json(content, provider=self.name, model=model)
        except Exception as exc:
            raise ExtractionError(f"Could not parse model output as JSON: {exc}") from exc
