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
    has_story: bool = Field(default=False, description="Есть человеческая история: конкретный герой (учёный, участник, человек), эксперимент с людьми или узнаваемая жизненная ситуация, а не сухой вывод")
    best_rubric: Rubric
    hook: str = Field(description="Идея хука для обложки на русском, до 90 символов")


class ScoreBatch(BaseModel):
    scores: list[ItemScore]


SlideType = Literal["cover", "lead", "insight", "person", "event", "statement", "stat", "list", "steps", "question", "cta"]


VizKind = Literal["none", "dots", "people", "network", "dandelion", "rings", "donut", "peaks", "house"]
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
        "dandelion — «одуванчик»: от центра (двор, дом) разлетаются точки-люди с линиями-связями, доля без связей выделена; "
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


VisualKind = Literal["stock", "stock_video", "our_video", "photo", "illustration", "map", "person",
                     "journal", "number", "quote"]


class Visual(BaseModel):
    """Одна иллюстрация фразы (~1,5 с на экране). Владелец: «каждую фразу иллюстрируют 2–3 картинки»."""
    kind: VisualKind = Field(description=(
        "stock — фото из фотостока по запросу; stock_video — короткое видео из стока; our_video — живой план "
        "со двора BIG Life (только если фраза про жизнь соседей во дворе); photo — фото из каталога «Фото для Reels»; "
        "illustration — иллюстрация из каталога; map — карта страны, где проходило исследование; person — фото "
        "исследователя из people; journal — обложка журнала, где вышло исследование; number — крупная цифра; "
        "quote — цитата исследователя или участника"))
    query: str = Field(description=(
        "stock / stock_video — конкретный запрос НА АНГЛИЙСКОМ, что в кадре, с полом и возрастом людей "
        "(«elderly woman reading with glasses», «eye chart on clinic wall»); map — страна по-английски («Japan»); "
        "person — name_en из people; photo / illustration — id из каталога; journal — название журнала; "
        "number — сама цифра («37%»); quote — текст цитаты по-русски; our_video — пусто"), max_length=200)
    caption: str = Field(default="", description="Короткая подпись на картинке, до 40 символов, или пусто", max_length=60)
    detail: str = Field(default="", description="map — город по-русски, если назван; journal — год и заголовок статьи; "
                                                "number — что означает цифра; person — роль; иначе пусто", max_length=160)


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
    visuals: list[Visual] = Field(default_factory=list, description=(
        "2–3 иллюстрации этой фразы, по порядку слов: каждая показывает то, о чём говорится в этот момент. "
        "Пол, возраст и обстановка — строго как в тексте"))
    shot: Literal["photo", "collage", "dataart"] = Field(default="collage", description=(
        "Кадр: photo — реальное фото во весь кадр с графикой поверх (узлы и связи, выноски, окна); "
        "collage — стол-коллаж: заметка с фактами, фото на скотче, карточка с данными, цифра, камера переходит "
        "между карточками; dataart — дата-арт на весь кадр (одуванчик, облако, кольца, пики, дом)"))
    photo_id: str = Field(default="", description="id реального фото из каталога фото для Reels (для photo — фон кадра, для collage — карточка) или пусто")
    note: list[str] = Field(default_factory=list, description="Для collage: 2–4 коротких факта на бумажную заметку («Чикаго», «3 000 жителей», «20 лет опросов»), только из источника")
    viz: VizSpec = Field(default_factory=VizSpec, description="Данные сцены: для photo — графика поверх фото (network, house), для collage — карточка с данными, для dataart — фигура на весь кадр")


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


# ---------- раскадровка режиссёра Reels (config/reels-motion.md) ----------

class Cut(BaseModel):
    """Перебивка в окне: появляется на слове word (за 0,3–0,7 с до него) и держится до следующей."""
    word: int = Field(description="Номер слова озвучки, которое называет то, что в кадре")
    kind: VisualKind
    query: str = Field(description=(
        "stock / stock_video — КОРОТКИЙ запрос к фотобанку НА АНГЛИЙСКОМ, 2–5 слов: главный предмет и пол/возраст "
        "(«elderly woman window», «reading glasses», «apartment stairwell»); ракурс, сезон и прочие детали — в must_show, "
        "длинные запросы фотобанк не находит; map — страна по-английски; person — name_en из people; "
        "photo / illustration — id из каталога; journal — название журнала; number — цифра («37%»); "
        "quote — цитата по-русски; our_video — пусто"), max_length=200)
    caption: str = Field(default="", description="Подпись на карточке до 40 символов (карта, цифра, журнал) или пусто", max_length=60)
    detail: str = Field(default="", description="map — город; journal — год; person — роль; number — что значит; иначе пусто", max_length=160)
    must_show: str = Field(default="", description=(
        "Для stock, stock_video, photo, our_video — что ОБЯЗАТЕЛЬНО должно быть в кадре, по-русски, для проверки "
        "картинки: «пожилая женщина, зима, без крупного лица»"), max_length=160)


Motion = Literal["punch", "flash", "marker", "circle"]


class Accent(BaseModel):
    word: int = Field(description="Номер слова, на котором срабатывает приём")
    motion: Motion = Field(description="punch — толчок картинки крупнее; flash — вспышка (не больше 2 за ролик, первая "
                                       "ставится автоматически после хука); marker — маркер под ключевым словом субтитра; "
                                       "circle — рукописная обводка в окне")


class AnchorState(BaseModel):
    word: int = Field(description="Номер слова про данные, на котором метафора меняет состояние (в формате 6 — начало главы)")
    until_word: int = Field(default=-1, description="Формат 6: номер слова, на котором глава данных заканчивается "
                                                    "(через 3–6 с после начала); -1 — через 4,5 с")
    viz: VizSpec


Icon = Literal["person", "elder", "eye", "glasses", "house", "window", "door", "heart", "cup", "phone", "book",
               "hand", "tree", "bench", "pill", "dog"]
Silhouette = Literal["circle", "eye", "house", "heart", "head"]


class ChartGroup(BaseModel):
    label: str = Field(description="Кто это, 1–4 слова: «теряют зрение», «видят хорошо»", max_length=40)
    value: float = Field(description="compare/scale — доля в группе с признаком, 0–100; timeline — значение в конце периода")
    start: float = Field(default=0, description="timeline — значение в начале периода; иначе 0")


class DataChapter(BaseModel):
    """Глава данных формата 6 (решения владельца 28.11): элементы — предметы темы, обязательно сравнение
    двух групп, время и одна крупная цифра. Только с цифрами из источника: нет цифр — нет глав."""
    word: int = Field(description="Номер слова, с которого начинается глава (слово про данные)")
    until_word: int = Field(description="Номер слова, на котором глава заканчивается (через 3–6 с)")
    chart: Literal["compare", "timeline", "scale"] = Field(description=(
        "compare — две группы рядом, у каждой доля с признаком; timeline — две линии во времени по годам; "
        "scale — масштаб исследования: силуэт из сотен значков-участников"))
    icon: Icon = Field(description="Значок-элемент: предмет темы (зрение — eye или glasses, дом — window, люди — person/elder)")
    silhouette: Silhouette = Field(default="circle", description="Во что складываются значки: форма темы")
    big: str = Field(description="Одна крупная цифра главы, как в источнике: «в 2 раза», «37%», «8 000», «10 лет»", max_length=24)
    big_caption: str = Field(description="Что значит крупная цифра, до 50 символов", max_length=70)
    groups: list[ChartGroup] = Field(description="Две группы для сравнения (для scale — одна)")
    years: list[int] = Field(default_factory=list, description="timeline — [год начала, год конца] из источника; иначе пусто")
    unit: str = Field(default="", description="Легенда: «1 значок = 100 человек» или пусто", max_length=50)
    evidence: str = Field(description="Дословная фраза из источника, где стоят эти цифры (для проверки)", max_length=400)


class Storyboard(BaseModel):
    metaphor: str = Field(description="Одной фразой: почему эта фигура — образ главной находки ролика", max_length=200)
    chapters: list[DataChapter] = Field(default_factory=list, description=(
        "Формат 6: главы данных, 0–3. Только если в источнике есть цифры; нет цифр — пустой список"))
    anchor: list[AnchorState] = Field(default_factory=list, description="1–4 состояния одной метафоры: первое — на первом слове после хука, "
                                                  "дальше только на словах про данные; kind во всех одинаковый")
    cuts: list[Cut] = Field(description="Перебивки в окне по порядку слов: на каждом названном существительном, "
                                        "в среднем раз в 1,5–2,5 с, не чаще раза в 0,8 с, ни одна не дольше 4,5 с")
    accents: list[Accent] = Field(default_factory=list, description="Толчки, маркеры, обводки, вторая вспышка")
    expand_word: int = Field(description="Номер слова, с которого метафора раскрывается на весь кадр (вывод, последние 3–5 с)")
    source: str = Field(default="", description="Строка источника внизу кадра: «Журнал, год» до 50 символов", max_length=80)


class PickVerdict(BaseModel):
    """Проверка картинок «по глазам»: какая из кандидатов показывает то, что нужно."""
    best: int = Field(description="Номер подходящей картинки (с 0) или -1, если не подходит ни одна")
    reason: str = Field(description="Одной-двумя фразами: почему выбрана или почему все не подходят", max_length=800)
    better_query: str = Field(default="", description=(
        "Если не подошла ни одна: новый запрос к фотобанку НА АНГЛИЙСКОМ, проще и короче (2–5 слов), по которому "
        "нужный кадр скорее найдётся: «elderly woman window», «reading glasses table». Иначе пусто"), max_length=120)
