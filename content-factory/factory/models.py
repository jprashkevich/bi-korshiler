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


SlideType = Literal["cover", "insight", "person", "event", "statement", "stat", "list", "steps", "question", "cta"]


class Slide(BaseModel):
    type: SlideType = Field(description=(
        "cover — обложка с хуком (первый слайд); insight — заголовок, текст и фото или иллюстрация; "
        "person — коллаж с фото исследователя или организации из people (заголовок — что он выяснил); "
        "event — мероприятие во дворе с реальным фото из отчёта (только для рубрики «Жизнь дворов»); "
        "statement — крупная фраза-вывод на цветном фоне; stat — одна большая цифра с пояснением; "
        "list — заголовок и 2–4 карточки (например фразы или факты); steps — заголовок и 3–4 шага; "
        "question — вопрос аудитории; cta — финальный слайд с призывом (последний слайд)"))
    eyebrow: str = Field(description="Короткая надпись над заголовком, 1–4 слова, без точки", max_length=40)
    title: str = Field(description="Заголовок слайда до 50 символов (обложка до 70). Для stat — сама цифра (например «52 000» или «в 2 раза»)", max_length=110)
    text: str = Field(description="Текст слайда до 160 символов: одна-две короткие фразы; пусто, если не нужен. Детали — в подпись к посту", max_length=300)
    items: list[str] = Field(description="Для list и steps: 3–4 пункта до 50 символов; иначе пустой список")
    item_labels: list[str] = Field(description="Для list: короткие подписи к пунктам (например «У подъезда»); иначе пустой список")
    illustration_id: str = Field(description="id иллюстрации из каталога для cover или insight, иначе пустая строка")
    person: str = Field(description="Для person: name_en из people; иначе пустая строка")
    photo_ref: str = Field(description="Для event (и cover в «Жизни дворов»): id фото из отчёта; иначе пустая строка")


class PostPackage(BaseModel):
    headline: str = Field(description="Тема поста одной строкой для контент-плана", max_length=120)
    accent: Accent
    photo_id: str = Field(description="id фото из каталога для слайда insight, или пустая строка, если фото или иллюстрация не подходят")
    people: list[PersonRef] = Field(description="Исследователи и организации, названные в источнике (0–3). Только реально упомянутые")
    slides: list[Slide]
    caption_ru: str = Field(description="Подпись к посту на русском: хук в первой строке, 3–5 коротких абзацев, призыв сохранить/отправить соседу, без эмодзи и без хэштегов", max_length=2000)
    hashtags: list[str] = Field(description="5–8 хэштегов без символа #, на русском или латиницей")
    summary_kz: str = Field(description="Краткое содержание на казахском, 2–3 предложения", max_length=500)
    summary_uz: str = Field(description="Краткое содержание на узбекском (латиница), 2–3 предложения", max_length=500)
    alt_text: str = Field(description="Alt-текст для карусели на русском, 1–2 предложения", max_length=300)
    source_line: str = Field(description="Источник для последнего слайда и подписи: издание/журнал, год; исследователи, если названы в источнике", max_length=220)
    threads: list[str] = Field(description="Тред для Threads: 3–5 сообщений, каждое до 450 символов, последнее — вопрос аудитории. Другая подача, чем в карусели, разговорный тон")
    fact_check: list[str] = Field(description="Каждое фактическое утверждение поста и где оно есть в источнике (для проверки человеком)")


SceneType = Literal["hook", "stat", "context", "person", "insight", "question", "cta"]


class Scene(BaseModel):
    type: SceneType = Field(description=(
        "hook — первая сцена, интрига за 1–2 секунды; stat — одна крупная цифра (title = сама цифра, "
        "например «52 000», «37%», «в 2 раза»); context — кто, где, сколько людей изучали; "
        "person — коллаж с фото исследователя или организации из people; "
        "insight — главный вывод; question — вопрос аудитории; cta — финальная сцена с призывом"))
    eyebrow: str = Field(description="Короткая надпись над текстом, 1–3 слова", max_length=30)
    title: str = Field(description="Крупный текст на экране, до 40 символов. Не повторяет озвучку слово в слово", max_length=60)
    text: str = Field(description="Вторая строка на экране, до 70 символов, или пусто. В сценах с иллюстрацией или фото — пусто", max_length=100)
    voice: str = Field(description="Что говорит голос в этой сцене: 1–2 коротких разговорных предложения на русском, до 18 слов", max_length=260)
    illustration_id: str = Field(description="id иллюстрации из каталога для hook, insight или cta, иначе пустая строка")
    person: str = Field(description="Для person: name_en из people; иначе пустая строка")


class ReelPackage(BaseModel):
    headline: str = Field(description="Тема ролика одной строкой для контент-плана", max_length=120)
    accent: Accent
    cover_title: str = Field(description="Текст обложки Reels, до 40 символов, интрига", max_length=50)
    people: list[PersonRef] = Field(description="Исследователи и организации, названные в источнике (0–3). Только реально упомянутые")
    scenes: list[Scene]
    caption_ru: str = Field(description="Подпись к Reels на русском: хук в первой строке, 2–4 коротких абзаца, призыв сохранить/отправить соседу, без эмодзи и хэштегов", max_length=1500)
    hashtags: list[str] = Field(description="5–8 хэштегов без символа #")
    summary_kz: str = Field(description="Краткое содержание на казахском, 2–3 предложения", max_length=500)
    summary_uz: str = Field(description="Краткое содержание на узбекском (латиница), 2–3 предложения", max_length=500)
    source_line: str = Field(description="Источник: издание/журнал, год; исследователи, если названы", max_length=220)
    threads: list[str] = Field(description="Тред для Threads: 3–5 сообщений до 450 символов, последнее — вопрос аудитории")
    fact_check: list[str] = Field(description="Каждое фактическое утверждение и где оно есть в источнике")
