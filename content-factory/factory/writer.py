"""Генерация пакета публикации: слайды, подпись, KZ/UZ, alt-текст, тред для Threads."""
from __future__ import annotations

import json
import logging

import yaml

from . import ingest, llm
from .models import PostPackage
from .settings import CONFIG_DIR, settings

log = logging.getLogger(__name__)


def load_yaml(name: str) -> dict:
    return yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8"))


def system_prompt() -> str:
    brand = (CONFIG_DIR / "brand.md").read_text(encoding="utf-8")
    photos = load_yaml("photos.yaml")["photos"]
    catalog = "\n".join(f"- {p['id']}: {p['desc']}" for p in photos)
    from .render import illustrations
    available = illustrations()
    ills = "\n".join(f"- {i['id']}: {i['desc']}" for i in load_yaml("illustrations.yaml").get("illustrations", [])
                     if i["id"] in available) or "- (пока нет)"
    return f"""Ты — ведущий автор Instagram-паблика BIG Life и специалист по вирусным каруселям.
Пишешь по-русски живо и коротко: на слайде читатель тратит 2–3 секунды.

{brand}

## Как устроена карусель
- Первый слайд — cover с хуком: интрига, контринтуитивный факт или узнаваемая ситуация из жизни во дворе. До 70 символов.
- Последний слайд — cta: вывод одной фразой и призыв сохранить пост или отправить соседу.
- Между ними раскрываем материал: каждый слайд — одна мысль. Чередуй светлые (insight, list) и цветные (statement, stat, steps) слайды.
- Ровно один слайд insight с фото, если в каталоге есть подходящее; иначе photo_id пустой и insight не используется.
- Заголовки слайдов до 60 символов, текст до 220 символов.
- Никаких эмодзи. Кавычки «ёлочки». Тире — длинное.

## Каталог реальных фото BIG Life
{catalog}

## Каталог иллюстраций BIG Life (изометрия в фирменных цветах)
{ills}

## Иллюстрации, люди и коллажи
- На обложку (cover) почти всегда ставь подходящую иллюстрацию: illustration_id. Это повышает узнаваемость ленты.
- Для слайда insight выбирай что-то одно: реальное фото BIG Life (photo_id) или иллюстрацию (illustration_id).
  Реальное фото — когда речь о жизни дворов, иллюстрация — когда об общей идее.
- Если в источнике назван исследователь или организация (университет, институт), добавь их в people
  и сделай один слайд person: коллаж с фото и подписью, а в заголовке — что этот человек или команда выяснили.
  Не придумывай людей; если в источнике никто не назван, people пустой и слайда person нет.
"""


def build_user_prompt(rubric_key: str, item: dict | None, article: str, feedback: list[str],
                      previous: dict | None) -> str:
    rubric = load_yaml("rubrics.yaml")["rubrics"][rubric_key]
    parts = [f"Рубрика: {rubric['title']}. Формат: карусель из {rubric['slides']} слайдов.",
             f"Задача рубрики: {rubric['brief']}"]
    if item:
        parts.append(f"Источник: {item['feed']}\nЗаголовок: {item['title']}\nСсылка: {item['url']}")
        hook = (item.get("score_data") or {}).get("hook")
        if hook:
            parts.append(f"Идея хука от редактора (можно улучшить): {hook}")
        parts.append(f"Аннотация из RSS:\n{item.get('summary') or '—'}")
        parts.append(f"Текст статьи (может быть неполным или пустым):\n{article or '—'}")
        parts.append("Используй только факты из источника выше. Если полного текста нет, опирайся на аннотацию "
                     "и не добавляй деталей, которых там нет.")
    else:
        parts.append("Внешнего источника нет: пост о продукте BIG Life на основе описания бренда. "
                     "source_line: «BIG Life».")
    if previous and feedback:
        parts.append("Предыдущая версия поста (JSON):\n" + json.dumps(previous, ensure_ascii=False))
        parts.append("Комментарии согласующего, которые нужно учесть:\n- " + "\n- ".join(feedback))
    return "\n\n".join(parts)


def write(rubric_key: str, item: dict | None, feedback: list[str] | None = None,
          previous: dict | None = None) -> PostPackage:
    article = ingest.fetch_article_text(item["url"]) if item else ""
    pkg = llm.ask(PostPackage, system=system_prompt(),
                  user=build_user_prompt(rubric_key, item, article, feedback or [], previous),
                  model=settings.writer_model, effort=settings.writer_effort)
    return normalize(pkg)


def normalize(pkg: PostPackage) -> PostPackage:
    """Мелкие правки, которые надёжнее сделать кодом: первый слайд — обложка, последний — CTA."""
    if pkg.slides and pkg.slides[0].type != "cover":
        pkg.slides[0].type = "cover"
    if pkg.slides and pkg.slides[-1].type != "cta":
        pkg.slides[-1].type = "cta"
    photo_ids = {p["id"] for p in load_yaml("photos.yaml")["photos"]}
    if pkg.photo_id not in photo_ids:
        pkg.photo_id = ""
    pkg.hashtags = [h.lstrip("#").replace(" ", "") for h in pkg.hashtags][:8]
    pkg.threads = [t.strip() for t in pkg.threads if t.strip()][:5]
    return pkg


REEL_RULES = """
## Как устроен сценарий Reels «Цифра дня»
- 5–6 сцен, общая озвучка 70–110 слов (25–40 секунд). Это голос живого человека из команды BIG Life:
  разговорно, тепло, короткими фразами, как будто рассказываешь соседу.
- Сцена 1 — hook: интрига за первые 2 секунды (вопрос или неожиданное утверждение).
- Одна сцена stat с главной цифрой из источника. Цифру не придумывать; если в источнике нет цифры,
  stat не используется, а главная мысль подаётся сценой insight.
- Затем context (кто изучал, сколько людей), insight (что это значит для жизни во дворе).
- Последняя сцена — cta или question: вопрос аудитории и призыв написать в комментариях или отправить ролик соседу.
- Текст на экране (title) короткий и не повторяет озвучку дословно: на экране — ключевые слова, в голосе — мысль.
- В озвучке без скобок, сокращений, латиницы и спецсимволов: «десять процентов», «Чикагский университет».
  Имена иностранных учёных — по-русски.
"""


def write_reel(rubric_key: str, item: dict | None, feedback: list[str] | None = None,
               previous: dict | None = None):
    from .models import ReelPackage
    article = ingest.fetch_article_text(item["url"]) if item else ""
    user = build_user_prompt(rubric_key, item, article, feedback or [], previous)
    user = user.replace("Формат: карусель", "Формат: Reels-ролик, а не карусель (количество слайдов игнорируй)", 1)
    pkg = llm.ask(ReelPackage, system=system_prompt() + REEL_RULES, user=user,
                  model=settings.writer_model, effort=settings.writer_effort)
    if pkg.scenes and pkg.scenes[0].type != "hook":
        pkg.scenes[0].type = "hook"
    pkg.hashtags = [h.lstrip("#").replace(" ", "") for h in pkg.hashtags][:8]
    pkg.threads = [t.strip() for t in pkg.threads if t.strip()][:5]
    return pkg
