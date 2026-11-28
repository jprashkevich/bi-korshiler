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


MONTHS_NOM = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август",
              "сентябрь", "октябрь", "ноябрь", "декабрь"]


def lessons_block() -> str:
    """Уроки прошлой недели из еженедельного отчёта (insights.report): что сохраняли и пересылали."""
    from . import db
    text = db.kv_get("learnings") or ""
    return f"## Обратная связь от аудитории\n{text}\n\n" if text else ""


def system_prompt() -> str:
    from .season import today as season_today
    brand = (CONFIG_DIR / "brand.md").read_text(encoding="utf-8")
    editorial = (CONFIG_DIR / "editorial.md").read_text(encoding="utf-8")
    from .season import fits
    photos = [p for p in load_yaml("photos.yaml")["photos"] if fits(p)]
    catalog = "\n".join(f"- {p['id']}: {p['desc']}" for p in photos) or "- (по сезону подходящих фото нет)"
    from .render import illustrations
    available = illustrations()
    ills = "\n".join(f"- {i['id']}: {i['desc']}" for i in load_yaml("illustrations.yaml").get("illustrations", [])
                     if i["id"] in available) or "- (пока нет)"
    return f"""Ты — ведущий автор Instagram-паблика BIG Life и специалист по вирусным каруселям.
Пишешь по-русски живо и по делу: короткими фразами, но с развёрнутой мыслью.

{brand}

{editorial}

## Как устроена карусель
- Первый слайд — cover с хуком: интрига, контринтуитивный факт или узнаваемая ситуация из жизни во дворе. До 70 символов.
- Последний слайд — cta: вывод одной фразой и призыв сохранить пост или отправить соседу.
  eyebrow cta — текст кнопки (например «Скачайте BIG App»). Источник на слайдах не пишем: он идёт в подпись.
- Название рубрики уже стоит на обложке отдельной меткой: eyebrow обложки его не повторяет
  (пиши тип материала или интригу: «Исследование», «Эксперимент», «Цифра недели»).
- Не повторяй одну и ту же мысль на соседних слайдах и в обложке: каждый слайд добавляет новое.
- Второй слайд — lead: лид из 2–3 предложений, расшифровка заголовка (title — короткая подводка, text — сам лид).
- Дальше основная часть по структуре статьи: анализ, история исследования (person, если назван человек),
  детали, вывод (statement), маленький шаг (steps). Каждый слайд развивает одну мысль до конца.
  Чередуй светлые (lead, insight, list) и цветные (statement, stat, steps) слайды.
- Ровно один слайд insight с фото, если в каталоге есть подходящее; иначе photo_id пустой и insight не используется.
- Лимиты: заголовок слайда до 60 символов (обложка до 70). Текст слайда без картинки (lead, insight без фото,
  statement, stat) — до 280 символов, 2–3 коротких предложения. Текст на слайде с фото или иллюстрацией — до 160.
  Пункты списков и шагов до 70. Короче делай фразы, а не мысль: обрубленная мысль хуже длинной.
- Подпись к посту — полная версия статьи на 900–1800 символов: лид, анализ с деталями, вывод, шаг, призыв.
  Источник — в подписи.
- Никаких эмодзи. Кавычки «ёлочки». Без длинного тире «—»: вместо него двоеточие, запятая или новая фраза.

## Сезон
Сейчас {MONTHS_NOM[season_today().month - 1]}. Картинки, сюжеты и советы — по сезону: в каталогах ниже оставлены
только подходящие к нему фото и иллюстрации. Если подходящей нет, оставь поле пустым, а не бери летнюю.

{lessons_block()}## Каталог реальных фото BIG Life
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
        parts.append("Сначала найди в полном тексте детали: сколько людей, где, сколько лет, как измеряли, "
                     "что удивило авторов. Построй сюжет поста вокруг них, а не пересказывай аннотацию.")
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
    from .season import fits
    photo_ids = {p["id"] for p in load_yaml("photos.yaml")["photos"] if fits(p)}
    if pkg.photo_id not in photo_ids:
        pkg.photo_id = ""
    pkg.hashtags = [h.lstrip("#").replace(" ", "") for h in pkg.hashtags][:8]
    pkg.threads = [t.strip() for t in pkg.threads if t.strip()][:5]
    return pkg


REEL_RULES = """
## Как устроен сценарий Reels
Reels публикуются как пробные: сначала их видят люди, которые BIG Life не знают. Ролик должен цеплять
без знания бренда, держать до конца и вызывать желание переслать соседу.

### Классическая структура (25–35 секунд, 8–10 сцен по 2–4 секунды)
1. hook (0–2 с) — смелое утверждение, развенчание мифа или цифра-шок. Голос начинает сразу с сути,
   без «привет», «сегодня расскажу», «знаете ли вы». title — до 6 слов огромным шрифтом.
   Хорошо: «Вы зря молчите в лифте», «Соседи важнее спортзала. Почти». Плохо: «Что будет, если…», «Интересный факт».
2. stakes (2–5 с) — почему это касается зрителя и открытая петля: обещание развязки в конце
   («а в конце — что с этим сделать за пять минут»).
3. Основная часть: 3 бита по 1–2 сцены — каждый бит новая мысль и новая картинка (fact, stat, myth/truth, person).
4. rehook ровно на середине — повторный крючок: «Но самое странное другое», «И вот тут учёные удивились».
5. payoff — развязка обещания из stakes и конкретное действие на сегодня.
6. cta — «Отправь соседу, который…» (конкретный типаж соседа). Последняя фраза перетекает в первую:
   ролик зациклен, при повторе фраза из cta естественно продолжается фразой из hook.

### Шаблоны (reel_format задан в задании, держись его)
- myth — «Миф / правда»: hook = миф, который все считают правдой; myth → truth с исследованием; payoff.
- number — «Цифра»: hook = цифра-шок (только из источника); stat со счётчиком; что за ней стоит; payoff.
- experiment — «Эксперимент»: hook = что сделали с людьми; как проверяли (кто, сколько, сколько времени);
  неожиданный результат; что повторить у себя во дворе.
- three — «3 вещи»: hook = «3 вещи, которые…»; три коротких бита (fact) по одному на вещь; payoff.

### Голос и экран
- Голос живой и быстрый: короткие фразы по 4–12 слов, разговорные обороты, вопросы к зрителю,
  обращение на «ты» в ролике допустимо. Всего 55–80 слов.
- Экран дополняет голос, а не дублирует: title — ключевые слова или цифра, highlight — одно ударное слово из title.
- Факты, цифры, имена — только из источника. Яркость — в подаче, не в выдумке.
- В озвучке без скобок, сокращений, латиницы и спецсимволов: «десять процентов», «Чикагский университет».
  Имена иностранных учёных — по-русски.
- music_mood выбери по теме: warm — тёплое и семейное, upbeat — бодрое и практичное, mystery — парадокс и интрига.
- BIG Life в кадре и в голосе — только в cta, не в начале.
"""


MAX_REEL_WORDS = 85      # речь ускорена до ~2,6 слова в секунду → не больше 35 секунд с паузой
REEL_FORMATS = ["myth", "number", "experiment", "three"]


def voice_words(pkg) -> int:
    return sum(len(sc.voice.split()) for sc in pkg.scenes)


FORMAT_TITLES = {"myth": "«Миф / правда»", "number": "«Цифра»", "experiment": "«Эксперимент»", "three": "«3 вещи»"}


def reel_format_for(day, item: dict | None) -> str:
    """Шаблоны по очереди по дням; «Цифра» — только если в источнике есть настоящая цифра."""
    fmt = REEL_FORMATS[day.toordinal() % len(REEL_FORMATS)]
    if fmt == "number" and not ((item or {}).get("score_data") or {}).get("has_number"):
        fmt = "myth"
    return fmt


def write_reel(rubric_key: str, item: dict | None, feedback: list[str] | None = None,
               previous: dict | None = None, reel_format: str = "myth"):
    from .models import ReelPackage
    article = ingest.fetch_article_text(item["url"]) if item else ""
    user = build_user_prompt(rubric_key, item, article, feedback or [], previous)
    user = user.replace("Формат: карусель", "Формат: Reels-ролик, а не карусель (количество слайдов игнорируй)", 1)
    user += f"\n\nreel_format: {reel_format} — шаблон {FORMAT_TITLES.get(reel_format, reel_format)}."
    pkg = llm.ask(ReelPackage, system=system_prompt() + REEL_RULES, user=user,
                  model=settings.writer_model, effort=settings.writer_effort)
    words = voice_words(pkg)
    if words > MAX_REEL_WORDS:   # озвучка дороже текста: сокращаем до синтеза, а не после
        user += (f"\n\n## Сократи\nВ прошлой версии озвучка была {words} слов, это больше 35 секунд. "
                 f"Сделай не больше {MAX_REEL_WORDS - 15} слов на весь ролик и не больше 10 сцен, смысл и факты сохрани.")
        pkg = llm.ask(ReelPackage, system=system_prompt() + REEL_RULES, user=user,
                      model=settings.writer_model, effort=settings.writer_effort)
    pkg.scenes = pkg.scenes[:10]
    pkg.reel_format = reel_format
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
  title — сама идея глаголом («Устройте чаепитие на этаже»); text — как это сделать за 2–3 короткие фразы:
  с кем, сколько времени, что взять и почему это сближает. Детали конкретные, а не «отличный способ познакомиться». Для каждой идеи выбери illustration_id из каталога, если подходит.
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
