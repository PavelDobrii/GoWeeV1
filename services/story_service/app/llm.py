"""Интеграция с ChatGPT и резервный генератор историй."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol, Sequence

try:
    from openai import OpenAI, OpenAIError
except ImportError:  # pragma: no cover - библиотека ставится опционально
    OpenAI = None  # type: ignore[assignment]
    OpenAIError = Exception  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class StoryGenerationError(Exception):
    """Ошибка при обращении к модели генерации."""


class StoryGenerator(Protocol):
    """Интерфейс генератора историй."""

    def generate(self, poi_id: int, lang: str, tags: Sequence[str]) -> str:
        """Вернуть текст истории для выбранной точки интереса."""


@dataclass
class _PromptContext:
    """Данные для построения промпта."""

    poi_id: int
    lang: str
    tags: Sequence[str]


class DummyStoryGenerator:
    """Простой генератор на случай отсутствия ключа API."""

    _WORDS = [
        "lorem",
        "ipsum",
        "dolor",
        "sit",
        "amet",
    ]

    def generate(self, poi_id: int, lang: str, tags: Sequence[str]) -> str:
        """Сформировать статический текст фиксированного объёма."""

        text = " ".join(self._WORDS * 60)
        return f"# История для POI {poi_id}\n\n{text}"


class ChatGPTStoryGenerator:
    """Клиент OpenAI ChatGPT для генерации историй."""

    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
        response_language: str,
        base_url: str | None = None,
    ) -> None:
        if OpenAI is None:
            raise StoryGenerationError(
                "Библиотека openai не установлена, интеграция недоступна"
            )
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._response_language = response_language

    def _build_messages(self, ctx: _PromptContext) -> list[dict[str, str]]:
        """Подготовить сообщения для Chat Completions."""

        tags_text = ", ".join(ctx.tags) if ctx.tags else ""
        system_prompt = (
            "Ты пишешь туристические мини-гиды. Используй живой русский язык, "
            "выделяй заголовок Markdown и не превышай 350 слов."
        )
        user_prompt = (
            "Сгенерируй рассказ о точке интереса с идентификатором {poi_id}. "
            "Опиши её историю, архитектуру и интересные факты."
        ).format(poi_id=ctx.poi_id)
        if tags_text:
            user_prompt += f" Учти теги: {tags_text}."
        user_prompt += (
            " Ответ верни на языке '{lang}' и соблюдай формат Markdown.".format(
                lang=ctx.lang or self._response_language
            )
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def generate(self, poi_id: int, lang: str, tags: Sequence[str]) -> str:
        """Вызвать ChatGPT и вернуть Markdown-историю."""

        ctx = _PromptContext(poi_id=poi_id, lang=lang, tags=tags)
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=self._build_messages(ctx),
                temperature=self._temperature,
                max_tokens=self._max_tokens,
            )
        except OpenAIError as exc:  # pragma: no cover - сетевые ошибки трудно воспроизвести
            logger.exception("Не удалось получить ответ от ChatGPT")
            raise StoryGenerationError("ChatGPT недоступен") from exc
        choice = response.choices[0]
        content = (choice.message.content or "").strip()
        if not content:
            raise StoryGenerationError("ChatGPT вернул пустой ответ")
        return content
