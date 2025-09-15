"""Клиент Google Text-to-Speech и вспомогательные функции."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Tuple

try:
    from google.api_core.exceptions import GoogleAPIError
    from google.cloud import texttospeech
except ImportError:  # pragma: no cover - библиотека устанавливается опционально
    GoogleAPIError = Exception  # type: ignore[assignment]
    texttospeech = None  # type: ignore[assignment]

from . import deps

logger = logging.getLogger(__name__)

_FORMATS: dict[str, Tuple[Any, str]] = {}
if texttospeech is not None:
    _FORMATS = {
        "mp3": (texttospeech.AudioEncoding.MP3, "mp3"),
        "ogg_opus": (texttospeech.AudioEncoding.OGG_OPUS, "ogg"),
        "linear16": (texttospeech.AudioEncoding.LINEAR16, "wav"),
    }


class TextToSpeechError(Exception):
    """Ошибка синтеза речи."""


class GoogleTextToSpeech:
    """Обёртка над официальным клиентом Google TTS."""

    def __init__(self, settings: deps.Settings) -> None:
        if texttospeech is None:
            raise TextToSpeechError(
                "Библиотека google-cloud-texttospeech не установлена"
            )
        if settings.google_credentials_path:
            self._client = texttospeech.TextToSpeechClient.from_service_account_file(
                settings.google_credentials_path
            )
        else:
            self._client = texttospeech.TextToSpeechClient()
        self._default_voice = settings.google_tts_voice
        self._default_language = settings.google_tts_language
        self._default_encoding, self._default_extension = self._parse_encoding(
            settings.google_tts_audio_encoding
        )
        self._speaking_rate = settings.google_tts_speaking_rate
        self._pitch = settings.google_tts_pitch
        self._effects_profile = settings.google_tts_effects_profile_id

    def _parse_encoding(self, value: str) -> Tuple[Any, str]:
        """Преобразовать строковое название формата в настройки клиента."""

        key = (value or "").lower()
        if key not in _FORMATS:
            raise TextToSpeechError(
                f"Неизвестный формат аудио '{value}'. Поддерживаются: {', '.join(_FORMATS)}."
            )
        return _FORMATS[key]

    def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        audio_format: str | None = None,
        language: str | None = None,
    ) -> tuple[bytes, str, int]:
        """Синтезировать речь и вернуть байты, расширение и примерную длительность."""

        if not text.strip():
            raise TextToSpeechError("Передан пустой текст для синтеза")
        encoding, extension = (
            self._parse_encoding(audio_format)
            if audio_format
            else (self._default_encoding, self._default_extension)
        )
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice_params = texttospeech.VoiceSelectionParams(
            language_code=language or self._default_language,
            name=voice or self._default_voice,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=encoding,
            speaking_rate=self._speaking_rate,
            pitch=self._pitch,
            effects_profile_id=[self._effects_profile] if self._effects_profile else None,
        )
        try:
            response = self._client.synthesize_speech(
                input=synthesis_input,
                voice=voice_params,
                audio_config=audio_config,
            )
        except GoogleAPIError as exc:  # pragma: no cover - сетевые ошибки сложно тестировать
            logger.exception("Ошибка Google TTS: %s", exc)
            raise TextToSpeechError("Google TTS вернул ошибку") from exc
        words = max(len(text.split()), 1)
        words_per_minute = 150 * max(self._speaking_rate, 0.5)
        duration_sec = max(int(words * 60 / words_per_minute), 1)
        return response.audio_content, extension, duration_sec


@lru_cache
def get_tts_client() -> GoogleTextToSpeech | None:
    """Создать и закешировать клиент Google TTS."""

    settings = deps.get_settings()
    try:
        return GoogleTextToSpeech(settings)
    except TextToSpeechError as exc:
        logger.warning("Google TTS недоступен: %s", exc)
        return None
