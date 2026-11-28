"""Схемы ответов модели: скоринг тем и пакет публикации."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Rubric = Literal["science", "practice", "number", "question"]
Accent = Literal["sky", "green", "orange", "periwinkle"]


class PersonRef(BaseModel):
    name_en: str = Field(description="Имя человека или название организации по-английски, как в английской Википедии")
    name_ru: str = Field(description="Как писать по-русски на слайде")
    role_ru: str = Field(description="Кто это: «психолог, Чикагский университет», «основатель Blue Zones», «университет в США»")
    kind: Literal["person", "org"]


class ItemScore(BaseModel):
    id: int
    relevance: int = Field(ge=0, le=10, description="Связь с соседством, сообществами, социальным здоровьем, одиночеством, долголетием, городской средой")
    virality: int = Field(ge=0, le=10, description="Удивительность, контринтуитивность, эмоция, желание переслать соседу")
    usefulness: int = Field(ge=0, le=10, description="Можно ли превратить в практический шаг для жителей двора")
    has_number: bool = Field(description="В заголовке или аннотации есть конкретная цифра из исследования")
    best_rubric: Rubric
    hook: str = Field(description="Идея хука для обложки на русском, до 90 символов")


class ScoreBatch(BaseModel):
    scores: list[ItemScore]


SlideType = Literal["cover", "lead", "insight", "person", "event", "statement", "stat", "list", "steps", "question", "cta"]


VizKind = Literal["none", "dots", "people", "network", "rings", "donut", "peaks", "house"]
VizColor = Literal["accent", "accent2", "white", "muted"]


class VizGroup(BaseModel):
    label: str = Field(description="Подпись группы, 1–3 слова: «знают соседей», «одиноки»", max_length=40)
    value: float = Field(description="Доля группы в процентах 0–100 (для rings — процент шкалы, для network — доля людей без связей)")
    color: VizColor = Field(description="accent — главная группа, accent2 — вторая, white — нейтральная, muted — фон/остальные")


class VizSpec(BaseModel):
    """Инфографика сцены: точки-люди, сеть связей, кольца процентов или дом с окнами.
    Рисуется кодом по этим числам, поэтому числа — только из источника (или conditional)."""
    kind: VizKind = Field(default="none", description=(
        "none — без инфографики; dots — облако точек, 1 точка = группа людей, цветом выделены доли; "
        "people — 50 пиктограмм людей, окрашенных по долям, крупные проценты внизу (для «каждый пятый»); "
        "network — люди и связи между ними, value первой группы = доля одиноких (без линий); "
        "donut — кольцевая диаграмма: целое на 2–4 части, total — число в центре; "
        "peaks — пики-треугольники с плашками процентов для сравнения 2–5 значений (до/после, группы); "
        "rings — концентрические кольца-шкалы для сравнения 1–3 процентов; "
        "house — фасад дома, окна загораются по доле (про дом, подъезд, соседей)"))
    mode: Literal["build", "split", "highlight"] = Field(default="build", description=(
        "build — фигура собирается; split — группы разъезжаются в отдельные облака; "
        "highlight — выделяется главная группа, остальное гаснет. Соседние сцены с той же фигурой "
        "перестраивают её: build → highlight → split"))
    total: int = Field(default=0, description="Сколько людей (или домов) за фигурой: число из источника, например 3000; 0 — неизвестно")
    unit: str = Field(default="", description="Легенда: «1 точка = 10 человек», «1 окно = 1 семья»", max_length=40)
    groups: list[VizGroup] = Field(default_factory=list, description="1–3 группы с долями из источника")
    callouts: list[str] = Field(default_factory=list, description="0–2 выноски до 30 символов к ключевым точкам")
    conditional: bool = Field(default=False, description="true — точных чисел в источнике нет, схема условная (на экране будет пометка «условно»)")


class Slide(BaseModel):
    type: SlideType = Field(description=(
        "cover — обложка с хуком (первый слайд); lead — второй слайд: лид из 2–3 предложений, расшифровка заголовка; insight — заголовок, текст и фото или иллюстрация; "
        "person — коллаж с фото исследователя или организации из people (заголовок — что он выяснил); "
        "event — мероприятие во дворе с реальным фото из отчёта (только для рубрики «Жизнь дворов»); "
        "statement — крупная фраза-вывод на цветном фоне; stat — одна большая цифра с пояснением; "
        "list — заголовок и 2–4 карточки (например фразы или факты); steps — заголовок и 3–4 шага; "
        "question — вопрос аудитории; cta — финальный слайд с призывом (последний слайд)"))
    eyebrow: str = Field(description="Короткая надпись над заголовком, 1–4 слова, без точки", max_length=40)
    title: str = Field(description="Заголовок слайда до 60 символов (обложка до 70). Для stat — сама цифра (например «52 000» или «в 2 раза»)", max_length=110)
    text: str = Field(description="Текст слайда: на слайде без картинки до 280 символов (2–3 коротких предложения, мысль развёрнута до конца), на слайде с фото или иллюстрацией до 160; пусто, если не нужен", max_length=420)
    items: list[str] = Field(description="Для list и steps: 3–4 пункта до 70 символов; иначе пустой список")
    item_labels: list[str] = Field(description="Для list: короткие подписи к пунктам (например «У подъезда»); иначе пустой список")
    illustration_id: str = Field(description="id иллюстрации из каталога для cover или insight, иначе пустая строка")
    person: str = Field(description="Для person: name_en из people; иначе пустая строка")
    photo_ref: str = Field(description="Для event (и cover в «Жизни дворов»): id фото из отчёта; иначе пустая строка")
    viz: VizSpec = Field(default_factory=VizSpec, description="Для stat: визуализация цифры точками, кольцами или домом; для остальных kind=none")


class PostPackage(BaseModel):
    headline: str = Field(description="Тема поста одной строкой для контент-плана", max_length=120)
    accent: Accent
    photo_id: str = Field(description="id фото из каталога для слайда insight, или пустая строка, если фото или иллюстрация не подходят")
    people: list[PersonRef] = Field(description="Исследователи и организации, названные в источнике (0–3). Только реально упомянутые")
    slides: list[Slide]
    caption_ru: str = Field(description="Подпись к посту на русском — полная версия статьи на 900–1800 символов: лид (первая строка — хук), анализ с деталями из источника, вывод, маленький шаг, призыв сохранить/отправить соседу. Короткие абзацы, без эмодзи и без хэштегов", max_length=2200)
    alt_headlines: list[str] = Field(default_factory=list, description="Два запасных варианта заголовка обложки, другие по подаче (до 70 символов)")
    hashtags: list[str] = Field(description="5–8 хэштегов без символа #, на русском или латиницей")
    summary_kz: str = Field(description="Краткое содержание на казахском, 2–3 предложения", max_length=500)
    summary_uz: str = Field(description="Краткое содержание на узбекском (латиница), 2–3 предложения", max_length=500)
    alt_text: str = Field(description="Alt-текст для карусели на русском, 1–2 предложения", max_length=300)
    source_line: str = Field(description="Источник для последнего слайда и подписи: издание/журнал, год; исследователи, если названы в источнике", max_length=220)
    threads: list[str] = Field(description="Тред для Threads: 3–5 сообщений, каждое до 450 символов, последнее — вопрос аудитории. Другая подача, чем в карусели, разговорный тон")
    fact_check: list[str] = Field(description="Каждое фактическое утверждение поста и где оно есть в источнике (для проверки человеком)")


SceneType = Literal["hook", "stakes", "myth", "truth", "stat", "fact", "rehook", "context", "person",
                    "insight", "payoff", "question", "cta"]
ReelFormat = Literal["myth", "number", "experiment", "three"]
MusicMood = Literal["warm", "upbeat", "mystery"]


class Scene(BaseModel):
    type: SceneType = Field(description=(
        "hook — первые 2 секунды: смелое утверждение, миф или цифра-шок; stakes — почему это касается зрителя "
        "и обещание развязки; myth — что все думают; truth — как на самом деле; stat — одна крупная цифра "
        "(title = сама цифра: «52 000», «37%», «в 2 раза»); fact — один факт или деталь исследования; "
        "rehook — повторный крючок в середине («Но самое странное другое»); person — коллаж с фото исследователя "
        "из people; payoff — развязка обещания и конкретное действие; question — вопрос зрителю; "
        "cta — финал: призыв отправить соседу, фраза перетекает в начало ролика. context и insight — старые типы"))
    eyebrow: str = Field(description="Короткая надпись над текстом, 1–3 слова", max_length=30)
    title: str = Field(description="Крупный текст на экране: до 6 слов (до 40 символов). Ключевые слова, а не дубль озвучки", max_length=60)
    highlight: str = Field(default="", description="Одно слово из title, которое подсветить акцентным цветом (самое ударное), или пусто")
    text: str = Field(description="Вторая строка на экране, до 70 символов, или пусто. В сценах с иллюстрацией или фото — пусто", max_length=100)
    voice: str = Field(description="Что говорит голос в этой сцене: одна короткая живая фраза, 4–12 слов, как в разговоре", max_length=200)
    illustration_id: str = Field(description="id иллюстрации из каталога для hook, insight или cta, иначе пустая строка")
    person: str = Field(description="Для person: name_en из people; иначе пустая строка")
    viz: VizSpec = Field(default_factory=VizSpec, description="Инфографика сцены (см. правила). В сцене с viz illustration_id пустой")


class ReelPackage(BaseModel):
    headline: str = Field(description="Тема ролика одной строкой для контент-плана", max_length=120)
    accent: Accent
    reel_format: ReelFormat = Field(default="number", description="Сценарный шаблон ролика (задан в задании)")
    voice_mode: Literal["voice", "music"] = Field(default="voice", description="Задано в задании: voice — с голосом, music — без голоса, только музыка и текст")
    length: Literal["short", "mid", "long"] = Field(default="mid", description="Задано в задании: целевая длина ролика")
    music_mood: MusicMood = Field(default="warm", description="Настроение фоновой музыки: warm — тёплое, upbeat — бодрое, mystery — интригующее")
    hook_options: list[str] = Field(default_factory=list, description="5 разных вариантов хука (до 8 слов каждый); лучший стоит в первой сцене")
    cover_title: str = Field(description="Текст обложки Reels, до 40 символов, интрига", max_length=50)
    people: list[PersonRef] = Field(description="Исследователи и организации, названные в источнике (0–3). Только реально упомянутые")
    scenes: list[Scene]
    caption_ru: str = Field(description="Подпись к Reels на русском: первая строка — фраза, которую набрали бы в поиске, затем 2–4 коротких абзаца истории и призыв переслать с конкретным типажом соседа (в голосе ролика призыва нет), без эмодзи и хэштегов", max_length=2200)
    hashtags: list[str] = Field(description="5–8 хэштегов без символа #")
    summary_kz: str = Field(description="Краткое содержание на казахском, 2–3 предложения", max_length=500)
    summary_uz: str = Field(description="Краткое содержание на узбекском (латиница), 2–3 предложения", max_length=500)
    source_line: str = Field(description="Источник: издание/журнал, год; исследователи, если названы (коротко, до 200 символов)", max_length=400)
    threads: list[str] = Field(description="Тред для Threads: 3–5 сообщений до 450 символов, последнее — вопрос аудитории")
    fact_check: list[str] = Field(description="Каждое фактическое утверждение и где оно есть в источнике")
