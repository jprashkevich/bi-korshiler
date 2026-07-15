/**
 * lang.js - RU / KZ language switcher
 * Elements with data-kz store Kazakh text.
 * Original Russian text is saved to data-ru on first init.
 */

(function () {
  'use strict';

  const STORAGE_KEY = 'liga_lang';
  let currentLang = localStorage.getItem(STORAGE_KEY) || 'ru';

  /* ------------------------------------------------
   * Init: save original RU text to data-ru
   * ------------------------------------------------ */
  function initLangData() {
    document.querySelectorAll('[data-kz]').forEach(el => {
      if (!el.hasAttribute('data-ru')) {
        el.setAttribute('data-ru', el.innerHTML);
      }
    });
  }

  /* ------------------------------------------------
   * Apply language
   * ------------------------------------------------ */
  function applyLang(lang) {
    document.querySelectorAll('[data-kz]').forEach(el => {
      const ru = el.getAttribute('data-ru') || el.innerHTML;
      const kz = el.getAttribute('data-kz') || ru;
      el.innerHTML = lang === 'kz' ? kz : ru;
    });

    // Switch placeholders (textarea / input) by language
    document.querySelectorAll('[data-kz-ph]').forEach(el => {
      if (!el.hasAttribute('data-ru-ph')) {
        el.setAttribute('data-ru-ph', el.getAttribute('placeholder') || '');
      }
      el.setAttribute('placeholder', lang === 'kz'
        ? el.getAttribute('data-kz-ph')
        : el.getAttribute('data-ru-ph'));
    });

    // Switch playbook/manual links by language
    document.querySelectorAll('[data-href-ru][data-href-kz]').forEach(el => {
      el.href = lang === 'kz'
        ? el.getAttribute('data-href-kz')
        : el.getAttribute('data-href-ru');
    });

    // Update <html lang> attribute
    document.documentElement.lang = lang === 'kz' ? 'kk' : 'ru';
    document.documentElement.setAttribute('data-lang', lang);

    // Highlight active button
    document.querySelectorAll('[data-lang-btn]').forEach(btn => {
      btn.classList.toggle('lang-btn--active', btn.dataset.langBtn === lang);
    });

    currentLang = lang;
    localStorage.setItem(STORAGE_KEY, lang);
  }

  /* ------------------------------------------------
   * Bind click handlers to language buttons
   * ------------------------------------------------ */
  function bindButtons() {
    document.querySelectorAll('[data-lang-btn]').forEach(btn => {
      btn.addEventListener('click', () => {
        const lang = btn.dataset.langBtn;
        if (lang !== currentLang) applyLang(lang);
      });
    });
  }

  /* ------------------------------------------------
   * Start
   * ------------------------------------------------ */
  document.addEventListener('DOMContentLoaded', () => {
    initLangData();
    bindButtons();
    applyLang(currentLang); // restore language from localStorage
  });

})();
