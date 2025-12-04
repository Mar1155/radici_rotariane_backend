"""Translation service helpers for chat messages."""

from __future__ import annotations

import logging
from dataclasses import dataclass
import html
from typing import List, Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class TranslationServiceError(Exception):
    """Base error for translation failures."""


class TranslationServiceNotConfigured(TranslationServiceError):
    """Raised when no translation provider is available."""


class TranslationProviderError(TranslationServiceError):
    """Raised when the upstream provider returns an error."""


@dataclass
class TranslationResult:
    text: str
    provider: str
    detected_source_language: Optional[str] = None


def normalize_language_code(language_code: str) -> str:
    """Returns a normalized lowercase language code (e.g. it, en)."""
    return language_code.split("-")[0].lower()


def supported_languages() -> List[str]:
    return [code.lower() for code in getattr(settings, "TRANSLATION_SUPPORTED_LANGUAGES", [])]


class BaseTranslationProvider:
    name = ""

    def is_configured(self) -> bool:
        raise NotImplementedError

    def translate(self, text: str, target_language: str) -> TranslationResult:
        raise NotImplementedError


class DeepLTranslationProvider(BaseTranslationProvider):
    name = "deepl"

    def __init__(self) -> None:
        self.api_key = getattr(settings, "DEEPL_API_KEY", None)
        self.api_url = getattr(settings, "DEEPL_API_URL", "https://api-free.deepl.com/v2/translate")
        self.timeout = getattr(settings, "TRANSLATION_HTTP_TIMEOUT", 10)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def translate(self, text: str, target_language: str) -> TranslationResult:
        payload = {
            "auth_key": self.api_key,
            "target_lang": target_language.upper(),
            "text": text,
        }
        try:
            response = requests.post(self.api_url, data=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            logger.exception("DeepL translation failed")
            raise TranslationProviderError("Errore durante la traduzione con DeepL") from exc

        translations = data.get("translations") or []
        if not translations:
            raise TranslationProviderError("DeepL non ha restituito risultati")

        entry = translations[0]
        return TranslationResult(
            text=entry.get("text", ""),
            provider=self.name,
            detected_source_language=(entry.get("detected_source_language") or "").lower() or None,
        )


class GoogleTranslateProvider(BaseTranslationProvider):
    name = "google"

    def __init__(self) -> None:
        self.api_key = getattr(settings, "GOOGLE_TRANSLATE_API_KEY", None)
        self.api_url = getattr(
            settings,
            "GOOGLE_TRANSLATE_API_URL",
            "https://translation.googleapis.com/language/translate/v2",
        )
        self.timeout = getattr(settings, "TRANSLATION_HTTP_TIMEOUT", 10)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def translate(self, text: str, target_language: str) -> TranslationResult:
        params = {"key": self.api_key}
        payload = {
            "q": text,
            "target": target_language.lower(),
            "format": "text",
        }
        try:
            response = requests.post(self.api_url, params=params, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            logger.exception("Google Translate request failed")
            raise TranslationProviderError("Errore durante la traduzione con Google Translate") from exc

        translations = (data.get("data") or {}).get("translations") or []
        if not translations:
            raise TranslationProviderError("Google Translate non ha restituito risultati")

        entry = translations[0]
        detected = entry.get("detectedSourceLanguage")
        translated_text = entry.get("translatedText", "")
        return TranslationResult(
            text=html.unescape(translated_text),
            provider=self.name,
            detected_source_language=detected.lower() if isinstance(detected, str) else None,
        )


def _get_provider_chain() -> List[BaseTranslationProvider]:
    providers_map = {
        "deepl": DeepLTranslationProvider(),
        "google": GoogleTranslateProvider(),
    }
    priority = [name.strip().lower() for name in getattr(settings, "TRANSLATION_PROVIDER_PRIORITY", ["deepl", "google"])]
    ordered = []
    for provider_name in priority:
        provider = providers_map.get(provider_name)
        if provider and provider.is_configured():
            ordered.append(provider)
    return ordered


def translate_text(text: str, target_language: str) -> TranslationResult:
    if not text.strip():
        raise TranslationProviderError("Il messaggio è vuoto, impossibile tradurre")

    normalized_language = normalize_language_code(target_language)
    if normalized_language not in supported_languages():
        raise TranslationProviderError("Lingua di destinazione non supportata")

    provider_chain = _get_provider_chain()
    if not provider_chain:
        raise TranslationServiceNotConfigured("Nessun provider di traduzione configurato")

    last_error: Optional[Exception] = None
    for provider in provider_chain:
        try:
            return provider.translate(text=text, target_language=normalized_language)
        except TranslationProviderError as exc:
            last_error = exc
            logger.warning("Translation failed with provider %s", provider.name, exc_info=True)
            continue

    if last_error:
        raise TranslationProviderError(str(last_error))
    raise TranslationProviderError("Impossibile completare la traduzione")


__all__ = [
    "translate_text",
    "TranslationResult",
    "TranslationServiceError",
    "TranslationServiceNotConfigured",
    "TranslationProviderError",
    "normalize_language_code",
    "supported_languages",
]
