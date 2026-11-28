"""Вызовы Claude со структурированным JSON-ответом, проверенным через Pydantic."""
from __future__ import annotations

import copy
import json
import logging
from typing import TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

_client: anthropic.Anthropic | None = None
_UNSUPPORTED = {"title", "default", "maxLength", "minLength", "maximum", "minimum",
                "maxItems", "minItems", "examples"}


class LLMError(RuntimeError):
    pass


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()   # ключ из ANTHROPIC_API_KEY
    return _client


def strict_schema(model: type[BaseModel]) -> dict:
    """JSON-схема для structured outputs: без $ref, с additionalProperties: false.
    Ограничения длины убираются из схемы, но проверяются Pydantic после ответа."""
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})

    def walk(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return walk(copy.deepcopy(defs[node["$ref"].split("/")[-1]]))
            out = {}
            for k, v in node.items():
                if k == "properties":   # имена полей (в т.ч. поле «title») не трогаем
                    out[k] = {name: walk(sub) for name, sub in v.items()}
                elif k not in _UNSUPPORTED:
                    out[k] = walk(v)
            node = out
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            return node
        if isinstance(node, list):
            return [walk(x) for x in node]
        return node

    return walk(schema)


def ask(model_cls: type[T], *, system: str, user: str | list, model: str, effort: str,
        max_tokens: int = 16000) -> T:
    """Один запрос с JSON-ответом по схеме model_cls. При ошибке валидации — одна повторная попытка.
    user — строка или список блоков контента (текст и изображения)."""
    messages = [{"role": "user", "content": user}]
    schema = strict_schema(model_cls)
    for attempt in range(2):
        # потоковый запрос: без него SDK не пускает длинные ответы (вычитка с полным humanizer-ru,
        # max_tokens 32k) — «Streaming is required for operations that may take longer than 10 minutes»
        with client().beta.messages.stream(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            thinking={"type": "adaptive"},
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",   # при отказе модели запрос автоматически выполнит резервная модель
        ) as stream:
            resp = stream.get_final_message()
        if resp.stop_reason == "refusal":
            raise LLMError(f"Модель отказалась отвечать: {resp.stop_details}")
        if resp.stop_reason == "max_tokens":
            raise LLMError("Ответ обрезан по max_tokens")
        text = "".join(b.text for b in resp.content if b.type == "text")
        try:
            return model_cls.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValidationError) as exc:
            log.warning("Ответ не прошёл проверку (попытка %s): %s", attempt + 1, exc)
            messages = messages + [
                {"role": "assistant", "content": text},
                {"role": "user", "content": f"Ответ не прошёл проверку: {exc}. Исправь и верни JSON целиком."},
            ]
    raise LLMError("Не удалось получить корректный ответ после повторной попытки")
