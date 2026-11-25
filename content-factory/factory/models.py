"""Схемы ответов модели: скоринг тем и пакет публикации."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Rubric = Literal["science", "practice", "number", "question"]
Accent = Literal["sky", "green", "orange", "periwinkle"]


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


SlideType = Literal["cover", "insight", "statement", "stat", "list", "steps", "question", "cta"]


class Slide(BaseModel):
    type: SlideType = Field(description=(
        "cover — обложка с хуком (первый слайд); insight — заголовок, текст и фото; "
        "statement — крупная фраза-вывод на цветном фоне; stat — одна большая цифра с пояснением; "
        "list — заголовок и 2–4 карточки (например фразы или факты); steps — заголовок и 3–4 шага; "
        "question — вопрос аудитории; cta — финальный слайд с призывом (последний слайд)"))
    eyebrow: str = Field(description="Короткая надпись над заголовком, 1–4 слова, без точки", max_length=40)
    title: str = Field(description="Заголовок слайда. Для stat — сама цифра (например «52 000» или «в 2 раза»)", max_length=110)
    text: str = Field(description="Основной текст слайда, до 260 символов; пусто, если не нужен", max_length=300)
    items: list[str] = Field(description="Для list и steps: 2–4 пункта до 70 символов; иначе пустой список")
    item_labels: list[str] = Field(description="Для list: короткие подписи к пунктам (например «У подъезда»); иначе пустой список")


class PostPackage(BaseModel):
    headline: str = Field(description="Тема поста одной строкой для контент-плана", max_length=120)
    accent: Accent
    photo_id: str = Field(description="id фото из каталога для слайда insight, или пустая строка, если фото не подходит")
    slides: list[Slide]
    caption_ru: str = Field(description="Подпись к посту на русском: хук в первой строке, 3–5 коротких абзацев, призыв сохранить/отправить соседу, без эмодзи и без хэштегов", max_length=2000)
    hashtags: list[str] = Field(description="5–8 хэштегов без символа #, на русском или латиницей")
    summary_kz: str = Field(description="Краткое содержание на казахском, 2–3 предложения", max_length=500)
    summary_uz: str = Field(description="Краткое содержание на узбекском (латиница), 2–3 предложения", max_length=500)
    alt_text: str = Field(description="Alt-текст для карусели на русском, 1–2 предложения", max_length=300)
    source_line: str = Field(description="Источник для последнего слайда и подписи: издание/журнал, год; исследователи, если названы в источнике", max_length=220)
    threads: list[str] = Field(description="Тред для Threads: 3–5 сообщений, каждое до 450 символов, последнее — вопрос аудитории. Другая подача, чем в карусели, разговорный тон")
    fact_check: list[str] = Field(description="Каждое фактическое утверждение поста и где оно есть в источнике (для проверки человеком)")
