# 🏮 Лига Добрососедства — Сайт регистрации

**Дворовой квест для жителей ЖК. 9 апреля — 11 мая 2026. Подведение итогов: 18 мая 2026.**  
*Ауласы бірдің ауасы бір — У общего двора общая атмосфера*

---

## ✅ Реализованные функции

- **Hero-секция** с радарной диаграммой (Chart.js) вместо SVG-юрты
- **Таймер** обратного отсчёта до старта / до конца квеста
- **Секция «О квесте»** — формат, даты, цели
- **Секция «7 цветов активностей»** — карточки с цветными маркерами
- **Секция «Как участвовать»** — 3 шага
- **Секция «Призы»** — ТОП-3 + подведение итогов + индивидуальные призы
- **Секция «Номинации»** — 8 командных номинаций + табличка во двор
- **Секция «Юрты дворов»** — радарные диаграммы по каждому ЖК с фильтром по городу
- **Секция «Следить за активностями»** — WhatsApp Community
- **Форма регистрации** с полями: Имя, WhatsApp, Город, ЖК (autocomplete)
- **Autocomplete** по ЖК — поиск на русском и английском
- **Блок успеха** после регистрации: показывает двор + кнопку вступления в группу
- **Двойная запись**: Tables API + Google Sheets (параллельно)
- **100% мобильная адаптация** (mobile-first)
- **Анимации** fade-in при скролле, burger-меню

---

## 📁 Структура файлов

```
index.html          — главная страница (лендинг)
css/
  style.css         — вся стилизация, дизайн-система
js/
  config.js         — ⚠️ КОНФИГУРАЦИЯ (заполнить перед запуском!)
  data.js           — загрузка справочника ЖК + autocomplete
  form.js           — логика формы регистрации + двойная запись
  charts.js         — радарные диаграммы Chart.js
  main.js           — навигация, таймер, анимации
```

---

## ⚙️ Настройка перед запуском

Откройте `js/config.js` и заполните:

```javascript
const CONFIG = {
  GOOGLE_SCRIPT_URL:        'https://script.google.com/macros/s/YOUR_ID/exec',
  GOOGLE_SHEETS_CSV:        'https://docs.google.com/.../pub?gid=...&single=true&output=csv',
  GOOGLE_SHEETS_DISPLAY_URL:'https://docs.google.com/spreadsheets/d/YOUR_ID',
  WHATSAPP_COMMUNITY:       'https://chat.whatsapp.com/YOUR_COMMUNITY_LINK',
  DEV_MODE: false, // ← переключить на false когда данные готовы
};
```

---

## 🔌 Google Apps Script (для записи участников)

Создайте скрипт в Google Sheets → Extensions → Apps Script:

```javascript
function doPost(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data  = JSON.parse(e.postData.contents);
  sheet.appendRow([
    data.date,
    data.name,
    data.phone,
    data.city,
    data.jk_name,
    data.yard_name,
    data.group_link
  ]);
  return ContentService
    .createTextOutput(JSON.stringify({ status: 'ok' }))
    .setMimeType(ContentService.MimeType.JSON);
}
```

Deploy → Web App → Execute as: Me → Access: Anyone → Скопировать URL.

---

## 📊 Формат Google Sheet для данных Юрт

Лист «Юрты» должен иметь заголовки в строке 1:

| JK_Name | City | Yard | Eco | Sport | Kids | Creative | Culture | Edu | Mutual |
|---------|------|------|-----|-------|------|----------|---------|-----|--------|
| Навои 37 | Астана | Двор №1 | 8 | 12 | 5 | 3 | 7 | 4 | 6 |

File → Share → Publish to web → CSV → скопировать URL в `GOOGLE_SHEETS_CSV`.

---

## 🗃️ Таблицы базы данных

### `jk_directory` — справочник ЖК
| Поле | Тип | Описание |
|------|-----|----------|
| id | text | Уникальный ID |
| city | text | Город |
| jk_name_ru | text | Название на русском |
| jk_name_en | text | Название на английском |
| jk_aliases | array | Дополнительные варианты написания |
| yard_name | text | Название двора |
| group_link | text | Ссылка на группу WhatsApp/Telegram |

### `participants` — участники
| Поле | Тип | Описание |
|------|-----|----------|
| name | text | Имя участника |
| phone | text | WhatsApp номер |
| city | text | Город |
| jk_id | text | ID ЖК |
| jk_name | text | Название ЖК |
| yard_name | text | Название двора |
| group_link | text | Ссылка на группу |
| registered_at | datetime | Дата регистрации |
| source | text | UTM-источник |

---

## 🏙️ Поддерживаемые города
- Астана
- Алматы
- Атырау
- Шымкент
- Ташкент

---

## 🏆 Призы и номинации

**ТОП-3 призовых места:**
1. 🥇 Мобильный кинотеатр (проектор + экран + пуфы)
2. 🥈 Электрический самовар (15-45 л + чайный набор)
3. 🥉 Мобильная аудиосистема PartyBox

**8 командных номинаций:**
Спортивный двор | Творческий двор | Эко-двор | Дружный двор |
Хранители традиций | Двор прогресса | Двор преображения | Двор активного Детства

---

## 🔜 Следующие шаги

- [ ] Заполнить `js/config.js` реальными URL
- [ ] Загрузить полный список ЖК в таблицу `jk_directory`
- [ ] Настроить Google Apps Script и получить webhook URL
- [ ] Создать и опубликовать Google Sheet с данными юрт
- [ ] Добавить ссылки на соцсети в footer
- [ ] Установить `DEV_MODE: false` в config.js

---

*© 2026 BI Service — Развиваем соседские сообщества*
