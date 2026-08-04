# КП: The Guests → ресторан Kantin (Астана)

Коммерческое предложение по 4-недельной программе постановки процессного управления
сервисом. Стоимость — 1 250 000 тенге в месяц. Кейс Paulaner Bräuhaus Almaty приведён
как social proof.

## Файлы

| Файл | Что это |
|------|---------|
| `kp-kantin.html` | Исходник. Вёрстка под печать A4, 6 страниц. |
| `KP_The_Guests_Kantin.pdf` | Готовый PDF — то, что отправляется клиенту. |

## Сборка PDF

```bash
/opt/pw-browsers/chromium-1194/chrome-linux/chrome \
  --headless --disable-gpu --no-sandbox --hide-scrollbars \
  --print-to-pdf=KP_The_Guests_Kantin.pdf --no-pdf-header-footer \
  --run-all-compositor-stages-before-draw --virtual-time-budget=8000 \
  file://$PWD/kp-kantin.html
```

## Подключение дизайн-системы The Guests

Вёрстка ходит только через токены в блоке `:root` и через `@font-face`, поэтому
подключение — механическое, править разметку не нужно.

Из проекта Claude Design `5be614bf-41ac-4d2a-a29f-a6c5d44a3135` нужны:

```
docs/kp/
├── fonts/TildaSans-{Light,Regular,Medium,Semibold,Bold,ExtraBold,Black}.ttf
├── assets/photos/expert-zhanna-p.png    → фото в блоке «Кто ведёт программу»
└── assets/logo/tgs-logo-white.png       → логотип на тёмной плашке обложки
```

Плюс `colors_and_type.css` — его значения заменяют временную палитру в `:root`
(`--ink`, `--ink-soft`, `--muted`, `--accent`, `--accent-d`, `--wash`, `--wash-2`,
`--line`, `--line-2`, `--dark`).

Пути в CSS уже прописаны: как только файлы лягут на место, шрифт и фото подхватятся
при следующей сборке. Пока файлов нет — работает фолбэк (Manrope) и серая плашка
на месте фото.

### Почему ассеты не подтянулись автоматически

`DesignSync` (claude_design MCP) в этом окружении не проходит авторизацию:
`/design-login` требует интерактивный терминал. Обходные пути проверены и не сработали —
бренд-кит The Guests в Canva отдаёт только прозрачный PNG без палитры, TildaSans
публично не отдаётся ни с `static.tildacdn.com`, ни с зеркал.

Разблокировать можно двумя способами:
1. В Claude Design нажать **«Send to Claude Code Web»** — проект приземлится в воркспейс;
2. Приложить файлы из списка выше в чат напрямую.

## Источники содержания

- 4-недельная программа и её раскладка по неделям — из PDF «Содержание работы»
  (шахматка недель восстановлена по заливке ячеек оригинала).
- Кейс, метрики и гипотезы — из отчёта по 1 этапу Paulaner Bräuhaus Almaty
  (период 01–26.07.2026) и из рейтинга официантов за июль 2026.
- В кейсе не приводятся имена сотрудников ресторана — только агрегированные показатели.
