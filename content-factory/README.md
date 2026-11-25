# Контент-завод BIG Life

Каждый день готовит 2 публикации для Instagram по рубрикатору и присылает их в Telegram-группу на согласование.
После «Одобрить» тред автоматически уходит в Threads, а SMM-щик вручную публикует карусель в Instagram.

```
RSS (22 ленты) → ИИ-скоринг тем → тексты (Claude) → слайды по дизайн-системе (Chromium)
   → Telegram: альбом + ZIP оригиналов + подпись + KZ/UZ + alt + тред + проверка фактов
   → кнопки: Одобрить / Переделать / Другая тема / Отклонить
   → Одобрить: тред в Threads, статус в Google Sheets
```

## Что приходит в Telegram

1. Альбом слайдов (превью) и ZIP со слайдами 1080×1350 в исходном качестве.
2. Подпись на русском с источником и хэштегами, готовая к копированию.
3. Краткое содержание на казахском и узбекском, alt-текст, тред для Threads, список фактов для проверки.
4. Кнопки:
   - **Одобрить** — публикует тред в Threads (если подключён), пост помечается одобренным.
   - **Переделать** — бот просит ответить комментарием и пересобирает пост с его учётом.
   - **Другая тема** — пост на следующую по рейтингу тему той же рубрики.
   - **Отклонить** — пост снимается.

Команды бота в группе: `/id` — показать chat_id и свой user_id; `/run` — собрать посты на сегодня вне расписания; `/threads` — подключить аккаунт Threads; `/status` — проверить настройки и версию кода.

## Рубрики и сетка

Настраиваются в `config/rubrics.yaml`: 14 слотов в неделю. Пока рубрика «Жизнь дворов» берёт материал
как «Наука о соседстве» (этап 2 — отчёты из Google Drive), «Цифра дня» выходит каруселью (этап 3 — Reels с озвучкой).

Голос бренда и запреты — `config/brand.md`, ленты — `config/feeds.yaml`, каталог фото — `config/photos.yaml`
(фото лежат в `images/` в корне репозитория; новое фото = файл в `images/` + строка с описанием в каталоге).

## Запуск на Render

Подробная пошаговая инструкция для команды — [SETUP.md](SETUP.md).

1. В Render: **New → Blueprint**, выбрать этот репозиторий. Render прочитает `render.yaml` из корня
   и создаст воркер `biglife-content-factory` и базу `biglife-factory-db`.
2. Заполнить секреты в Environment воркера (в репозиторий их не коммитим):

| Переменная | Что это |
|---|---|
| `ANTHROPIC_API_KEY` | Ключ Claude API (console.anthropic.com) |
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather |
| `TELEGRAM_CHAT_ID` | id группы (добавьте бота в группу и отправьте `/id`) |
| `TELEGRAM_APPROVER_IDS` | user_id тех, кто может нажимать кнопки, через запятую |
| `THREADS_APP_ID`, `THREADS_APP_SECRET` | Ключи приложения Threads из кабинета Meta. Сам аккаунт подключается командой `/threads` в боте; токен продлевается автоматически |
| `GOOGLE_SERVICE_ACCOUNT_JSON`, `GOOGLE_SHEET_ID` | Необязательно: контент-план в Google Sheets (таблицу расшарить на email сервисного аккаунта) |

Необязательные настройки: `DAILY_RUN_HOUR` (по умолчанию 6:00 по Алматы), `POSTS_PER_DAY`,
`WRITER_MODEL` / `SCORER_MODEL` (по умолчанию `claude-opus-5-5`), `WRITER_EFFORT` (`high`), `SCORER_EFFORT` (`low`).

Чтобы бот видел ответы на свои сообщения в группе, у @BotFather отключите Group Privacy или сделайте бота админом группы.

## Локально

```bash
cd content-factory
pip install -r requirements-dev.txt && playwright install chromium
pytest -q                                   # офлайн-тесты
python -m factory ingest                    # собрать RSS
python -m factory score && python -m factory top   # нужен ANTHROPIC_API_KEY
python -m factory render tests/fixtures/sample_package.json   # рендер без Claude
python -m factory worker                    # бот + расписание
```

## Этапы

- [x] Этап 1: RSS, скоринг, карусели, Telegram с кнопками, Threads, Google Sheets.
- [ ] Этап 2: рубрика «Жизнь дворов» из отчётов в Google Drive.
- [ ] Этап 3: Reels «Цифра дня» с анимацией и озвучкой голосом через ElevenLabs.
- [ ] Этап 4: еженедельный отчёт и учёт метрик Instagram при выборе тем.

## Важно

- Шрифт `templates/assets/TT_Firs_Neue_Trial_Var_Roman.ttf` — пробная версия из дизайн-системы.
  Для публикаций нужна коммерческая лицензия TT Firs Neue; после покупки замените файл.
- Ленты Cambridge, APA News, PositivePsychology и The Guardian блокируют серверные запросы (отключены в `feeds.yaml`).
