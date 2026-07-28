/* ═══════════════════════════════════════════════════════════
   Веб-аналитика: Google Analytics 4 + Яндекс Метрика + конверсии
   ЗАМЕНИТЬ плейсхолдеры на реальные ID (см. GA_ID и YM_ID ниже)
   ═══════════════════════════════════════════════════════════ */

var GA_ID = 'G-XXXXXXXXXX';   // ← Measurement ID из Google Analytics 4
var YM_ID = 00000000;         // ← номер счётчика Яндекс Метрики

/* ── Google Analytics 4 ── */
(function () {
  if (!GA_ID || GA_ID.indexOf('XXXX') > -1) return;      // не инициализировать с плейсхолдером
  var s = document.createElement('script');
  s.async = true;
  s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
  document.head.appendChild(s);
  window.dataLayer = window.dataLayer || [];
  window.gtag = function () { dataLayer.push(arguments); };
  gtag('js', new Date());
  gtag('config', GA_ID);
})();

/* ── Яндекс Метрика ── */
(function (m, e, t, r, i, k, a) {
  if (!YM_ID || YM_ID === 00000000) return;              // не инициализировать с плейсхолдером
  m[i] = m[i] || function () { (m[i].a = m[i].a || []).push(arguments); };
  m[i].l = 1 * new Date();
  for (var j = 0; j < document.scripts.length; j++) { if (document.scripts[j].src === r) return; }
  k = e.createElement(t); a = e.getElementsByTagName(t)[0];
  k.async = 1; k.src = r; a.parentNode.insertBefore(k, a);
})(window, document, 'script', 'https://mc.yandex.ru/metrika/tag.js', 'ym');
if (YM_ID && YM_ID !== 00000000) {
  ym(YM_ID, 'init', { clickmap: true, trackLinks: true, accurateTrackBounce: true, webvisor: true });
}

/* ── Единая отправка конверсии в оба сервиса ── */
function trackConversion(goal) {
  if (window.gtag) gtag('event', goal);
  if (window.ym && YM_ID && YM_ID !== 00000000) ym(YM_ID, 'reachGoal', goal);
  if (window.console) console.log('[conversion]', goal);
}

/* ── Навешивание событий на форму-конструктор идей ── */
document.addEventListener('DOMContentLoaded', function () {
  var started = false;
  function formStart() { if (!started) { started = true; trackConversion('form_start'); } }

  // Начало заполнения: выбор направления или ввод текста
  document.querySelectorAll('.idea-chip').forEach(function (c) {
    c.addEventListener('click', formStart);
  });
  var ta = document.getElementById('ideaText');
  if (ta) ta.addEventListener('focus', formStart);

  // Отправка формы (главная конверсия) — «Отправить в WhatsApp»
  var send = document.getElementById('ideaSend');
  if (send) send.addEventListener('click', function () { trackConversion('form_submit'); });

  // Прямое обращение к координатору в WhatsApp — лид
  document.querySelectorAll('.wa-direct').forEach(function (w) {
    w.addEventListener('click', function () { trackConversion('contact_whatsapp'); });
  });

  // Клик «Стать амбассадором» / CTA, ведущие на форму — интерес
  document.querySelectorAll('a[href="#idea"]').forEach(function (a) {
    a.addEventListener('click', function () { trackConversion('cta_click'); });
  });
});
