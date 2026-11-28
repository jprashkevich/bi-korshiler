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
  eyebrow cta — текст кнопки (например «Скачайте BIG App»). Источник на слайдах не пишем: он идёт в подпись.
- Название рубрики уже стоит на обложке отдельной меткой: eyebrow обложки его не повторяет
  (пиши тип материала или интригу: «Исследование», «Эксперимент», «Цифра недели»).
- Не повторяй одну и ту же мысль на соседних слайдах и в обложке: каждый слайд добавляет новое.
- Между ними раскрываем материал: каждый слайд — одна мысль. Чередуй светлые (insight, list) и цветные (statement, stat, steps) слайды.
- Ровно один слайд insight с фото, если в каталоге есть подходящее; иначе photo_id пустой и insight не используется.
- Заголовки слайдов до 50 символов (обложка до 70), текст слайда до 160 символов, пункты списков до 50.
  Слайд читают с телефона за 2–3 секунды: лучше короче. Подробности, цифры и источник — в подпись к посту.
- Никаких эмодзи. Кавычки «ёлочки». Без длинного тире «—»: вместо него двоеточие, запятая или новая фраза.

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
- 5–6 сцен, общая озвучка 60–85 слов: ролик должен уложиться в 25–40 секунд, длиннее досматривают хуже.
  В каждой сцене одно-два коротких предложения, не больше 18 слов на сцену. Это голос живого человека из команды BIG Life:
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


MAX_REEL_WORDS = 90      # ~2,3 слова в секунду у русской озвучки → 40 секунд с паузой в конце


def voice_words(pkg) -> int:
    return sum(len(sc.voice.split()) for sc in pkg.scenes)


def write_reel(rubric_key: str, item: dict | None, feedback: list[str] | None = None,
               previous: dict | None = None):
    from .models import ReelPackage
    article = ingest.fetch_article_text(item["url"]) if item else ""
    user = build_user_prompt(rubric_key, item, article, feedback or [], previous)
    user = user.replace("Формат: карусель", "Формат: Reels-ролик, а не карусель (количество слайдов игнорируй)", 1)
    pkg = llm.ask(ReelPackage, system=system_prompt() + REEL_RULES, user=user,
                  model=settings.writer_model, effort=settings.writer_effort)
    words = voice_words(pkg)
    if words > MAX_REEL_WORDS:   # озвучка дороже текста: сокращаем до синтеза, а не после
        user += (f"\n\n## Сократи\nВ прошлой версии озвучка была {words} слов, это больше 40 секунд. "
                 f"Сделай не больше {MAX_REEL_WORDS - 10} слов на весь ролик и не больше 6 сцен, смысл и факты сохрани.")
        pkg = llm.ask(ReelPackage, system=system_prompt() + REEL_RULES, user=user,
                      model=settings.writer_model, effort=settings.writer_effort)
    pkg.scenes = pkg.scenes[:6]
    if pkg.scenes and pkg.scenes[0].type != "hook":
        pkg.scenes[0].type = "hook"
    pkg.hashtags = [h.lstrip("#").replace(" ", "") for h in pkg.hashtags][:8]
    pkg.threads = [t.strip() for t in pkg.threads if t.strip()][:5]
    return pkg


COURTYARD_RULES = """
## Рубрика «Жизнь дворов»: фото-дайджест
Ниже — свежие мероприятия во дворах BIG Life: ЖК, дата, название активности и реальные фото из отчётов.
- Карусель до 12 слайдов: cover → по одному слайду event на каждое мероприятие из списка (до 10) → cta.
- Для каждого event выбери лучшее фото этого мероприятия (photo_ref = id фото из списка) и напиши
  заголовок (что происходило, живо и по-соседски) и 1–2 предложения текста.
- Опирайся на «Описание из отчёта» и фото. Число участников, место и партнёра бери только из отчёта.
  Не придумывай имена, цитаты и детали, которых нет ни в отчёте, ни на фото. Атмосферу и эмоции можно по фото.
- Имена Драйверов и организаторов из отчёта можно упомянуть с благодарностью. Имена других жителей не пиши.
  Контакты (телефоны, почты) в посты не попадают никогда.
- Фото в списке уже отсортированы: первое у каждого мероприятия — лучшее по оценке, бери его, если оно подходит.
- eyebrow для event: «ДД.ММ · Название ЖК». Город на слайд ставится автоматически, в eyebrow его не пиши.
- В заголовке обложки или подписи можно назвать города недели («Астана, Шымкент и Ташкент»), если они указаны.
  В хэштеги добавь города латиницей или кириллицей (например Астана, Шымкент), только указанные в списке.
- Для cover выбери photo_ref самого яркого фото; заголовок — общий хук недели во дворах.
- Фото для слайда должно быть чистым кадром с места. НЕ БЕРИ: записи и снимки экрана, кадры с камер видеонаблюдения,
  фото с наложенным интерфейсом (время, скорость сети, «Camera», значки приложений, рамки мессенджеров), афиши,
  документы, размытые и тёмные кадры, крупные лица детей. Если у мероприятия нет ни одного чистого кадра —
  не делай для него слайд event вообще.
- Не используй illustration_id в этой рубрике; photo_id из каталога — тоже нет.
- people пустой, слайдов person нет. source_line: «Фотоотчёты BIG Life».
"""


def write_courtyard(events: list[dict], feedback: list[str] | None = None, previous: dict | None = None):
    """Фото-дайджест по мероприятиям из Drive. Фото передаются модели как изображения."""
    import base64
    import io
    from PIL import Image
    from . import drive
    from .models import PostPackage
    content: list[dict] = [{"type": "text", "text": build_user_prompt("courtyard", None, "", feedback or [], previous)
                            .replace("Внешнего источника нет: пост о продукте BIG Life на основе описания бренда. "
                                     "source_line: «BIG Life».", "Источник — фотоотчёты ниже.")}]
    for ev in events:
        rep = ev.get("report") or {}
        info = [f"\nМероприятие: {ev['label']}" + (f" (ещё {ev['videos']} видео)" if ev.get("videos") else "")]
        info.append(f"Город: {ev.get('city') or 'не указан'}")
        for key, label in (("description", "Описание из отчёта"), ("participants", "Участников"),
                           ("initiative", "Чья инициатива"), ("place_partner", "Место / партнёр"),
                           ("team", "Команда")):
            if rep.get(key):
                info.append(f"{label}: {rep[key]}")
        content.append({"type": "text", "text": "\n".join(info)})
        for ph in ev["photos"]:
            path = drive.download(ph["id"])
            im = Image.open(path)
            im.thumbnail((768, 768))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=80)
            content.append({"type": "text", "text": f"Фото id={ph['id']}:"})
            content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                        "data": base64.b64encode(buf.getvalue()).decode()}})
    pkg = llm.ask(PostPackage, system=system_prompt() + COURTYARD_RULES, user=content,
                  model=settings.writer_model, effort=settings.writer_effort)
    valid = {ph["id"] for ev in events for ph in ev["photos"]}
    for sl in pkg.slides:
        if sl.photo_ref not in valid:
            sl.photo_ref = ""
    # слайд мероприятия без годного фото выбрасываем: пустая плашка хуже, чем на одно мероприятие меньше
    pkg.slides = [sl for sl in pkg.slides if not (sl.type == "event" and not sl.photo_ref)]
    if sum(sl.type == "event" for sl in pkg.slides) < 2:
        raise llm.LLMError("В отчётах недели меньше двух мероприятий с чистыми фото — дайджест не собран")
        sl.illustration_id = ""
    pkg.photo_id = ""
    pkg.people = []
    return normalize(pkg)


IDEAS_RULES = """
## Рубрика «Идеи на выходные» (выходит в пятницу утром)
- Карусель 7–8 слайдов: cover → 5–6 слайдов insight (одна идея на слайд) → cta.
- Обложка: заголовок с датами («Идеи на выходные 29–30 ноября и неделю»), illustration_id — подходящая по сезону.
- Слайд идеи: eyebrow — когда («Суббота», «Воскресенье», «В будни», «Каждый вечер»);
  title — сама идея глаголом («Устройте чаепитие на этаже»); text — как это сделать за 1–2 фразы:
  с кем, сколько времени, что взять. Для каждой идеи выбери illustration_id из каталога, если подходит.
- Идеи разные по формату: на улице и дома, для детей и для старших, на 10 минут и на вечер.
  Учитывай сезон и погоду этого месяца в Казахстане и Узбекистане, а также праздники из календаря.
- Если даны «что делали соседи на этой неделе» — одну-две идеи можно продолжить от них
  («во дворах уже катались на коньках — позовите соседей на каток»), без имён жителей.
- Если дан научный факт из ленты, его можно привести в подписи как «почему это работает», только по источнику.
- people пустой, слайдов person нет. source_line: «BIG Life» или источник научного факта, если он использован.
- В подписи — коротко все идеи списком, чтобы их можно было сохранить.
"""


def write_ideas(day, feedback: list[str] | None = None, previous: dict | None = None):
    """Пятничные идеи на выходные и следующую неделю: сезон, праздники, что делали соседи, практичная наука."""
    from datetime import timedelta
    from . import db, drive
    from .models import PostPackage
    months = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября",
              "октября", "ноября", "декабря"]
    sat, sun = day + timedelta(days=(5 - day.weekday()) % 7), day + timedelta(days=(6 - day.weekday()) % 7)
    week_end = sun + timedelta(days=7)
    fmt = lambda d: f"{d.day} {months[d.month - 1]}"
    cal = load_yaml("calendar.yaml").get("dates", {})
    occasions = []
    d = day
    while d <= week_end:
        if f"{d.month:02d}-{d.day:02d}" in cal:
            occasions.append(f"{fmt(d)}: {cal[f'{d.month:02d}-{d.day:02d}']}")
        d += timedelta(days=1)
    parts = [build_user_prompt("weekend", None, "", feedback or [], previous)
             .replace("Внешнего источника нет: пост о продукте BIG Life на основе описания бренда. "
                      "source_line: «BIG Life».", ""),
             f"Сегодня пятница, {fmt(day)}. Выходные: {fmt(sat)}–{fmt(sun)}. Следующая неделя: до {fmt(week_end)}.",
             "Поводы в эти даты: " + ("; ".join(occasions) if occasions else "нет")]
    try:   # что делали соседи — для вдохновения, без имён
        evs = drive.recent_events(days=10, include_used=True) if drive.enabled() else []
        acts = sorted({e.activity for e in evs if e.activity})[:25]
        if acts:
            parts.append("Что делали соседи во дворах BIG Life за последние 10 дней (названия активностей): "
                         + ", ".join(acts))
    except Exception as exc:
        log.info("Активности из Drive для идей недоступны: %s", exc)
    try:   # одна свежая практичная научная находка
        from . import score
        it = score.pick("practice", prefer_kind="popular")
        if it:
            parts.append(f"Научный факт недели (можно использовать в подписи): {it['title']} — "
                         f"{(it.get('summary') or '')[:500]} (источник: {it['feed']}, {it['url']})")
    except Exception as exc:
        log.info("Научный факт для идей недоступен: %s", exc)
    pkg = llm.ask(PostPackage, system=system_prompt() + IDEAS_RULES, user="\n\n".join(parts),
                  model=settings.writer_model, effort=settings.writer_effort)
    pkg.people = []
    return normalize(pkg)
