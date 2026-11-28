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


# ---------- учёт расхода (решение владельца 28.11: баланс API кончился, решаем по цифрам) ----------
# $ за миллион токенов: вход, выход, чтение кэша. Запись в кэш — 1,25 цены входа.
PRICES = {"claude-opus-5-5": (4.0, 20.0, 0.20), "claude-haiku-5-5": (0.10, 0.50, 0.01)}
CURRENT_POST: int | None = None      # чей это расход: pipeline ставит номер поста на время его сборки


def cost(model: str, u) -> float:
    pin, pout, pread = PRICES.get(model, PRICES["claude-opus-5-5"])
    cw = getattr(u, "cache_creation_input_tokens", 0) or 0
    cr = getattr(u, "cache_read_input_tokens", 0) or 0
    return (u.input_tokens * pin + cw * pin * 1.25 + cr * pread + u.output_tokens * pout) / 1e6


def _record(model: str, purpose: str, u) -> None:
    try:
        from . import db
        with db.engine.begin() as c:
            c.execute(db.usage.insert().values(
                at=db.now(), post_id=CURRENT_POST, purpose=purpose[:60], model=model[:60],
                input_tokens=u.input_tokens, output_tokens=u.output_tokens,
                cache_write=getattr(u, "cache_creation_input_tokens", 0) or 0,
                cache_read=getattr(u, "cache_read_input_tokens", 0) or 0, usd=round(cost(model, u), 5)))
    except Exception as exc:      # учёт не должен ронять генерацию
        log.info("Расход не записан: %s", exc)


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
        # при отказе модели запрос автоматически выполнит резервная модель; у Haiku серверного
        # переключения нет — для неё параметр не передаём, иначе API отвечает ошибкой
        extra = {} if model.startswith("claude-haiku") else {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
        with client().beta.messages.stream(
            model=model,
            max_tokens=max_tokens,
            # кэш: большие правила (humanizer-ru ~35 тыс. токенов, «Ремесло Reels») уходят 3–4 раза за сборку
            # ролика; из кэша они стоят 5–10% цены. Короткие подсказки кэш просто не возьмёт — это не ошибка
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=messages,
            thinking={"type": "adaptive"},
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
            **extra,
        ) as stream:
            resp = stream.get_final_message()
        _record(getattr(resp, "model", None) or model, model_cls.__name__, resp.usage)
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
