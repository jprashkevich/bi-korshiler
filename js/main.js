/**
 * main.js — навигация, анимации, FAQ, конструктор идеи (WhatsApp)
 */

document.addEventListener('DOMContentLoaded', () => {
  initNav();
  initScrollAnimations();
  initFaq();
  initIdeaBuilder();
  initActivityCards();
  initHeroSlider();
  initAboutSlider();
  initGallerySlider();
});

/* =====================================================
   NAVIGATION
   ===================================================== */
function initNav() {
  const header = document.querySelector('.header');
  const burger = document.getElementById('burger');
  const nav    = document.getElementById('mainNav');

  // Scroll shadow
  window.addEventListener('scroll', () => {
    if (window.scrollY > 20) {
      header?.classList.add('scrolled');
    } else {
      header?.classList.remove('scrolled');
    }
  }, { passive: true });

  // Burger toggle
  if (burger && nav) {
    burger.addEventListener('click', () => {
      burger.classList.toggle('active');
      nav.classList.toggle('mobile-open');
    });

    // Close on nav link click
    nav.querySelectorAll('.nav__link').forEach(link => {
      link.addEventListener('click', () => {
        burger.classList.remove('active');
        nav.classList.remove('mobile-open');
      });
    });

    // Close on outside click
    document.addEventListener('click', (e) => {
      if (!header?.contains(e.target)) {
        burger.classList.remove('active');
        nav.classList.remove('mobile-open');
      }
    });
  }

  // Active nav link on scroll
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('.nav__link[href^="#"]');

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.id;
        navLinks.forEach(link => {
          link.classList.toggle(
            'nav__link--active',
            link.getAttribute('href') === `#${id}`
          );
        });
      }
    });
  }, { threshold: 0.35 });

  sections.forEach(s => observer.observe(s));

  // Smooth scroll for all anchor links
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', (e) => {
      const href = anchor.getAttribute('href');
      if (href === '#') return;
      const target = document.querySelector(href);
      if (!target) return;
      e.preventDefault();
      const offset = 70; // header height
      const top = target.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top, behavior: 'smooth' });
    });
  });
}

/* =====================================================
   SCROLL ANIMATIONS (Intersection Observer)
   ===================================================== */
function initScrollAnimations() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const delay = entry.target.dataset.delay || 0;
        setTimeout(() => {
          entry.target.classList.add('visible');
        }, delay);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

  // Cascade animation for grid cards
  document.querySelectorAll('.fade-in').forEach(el => {
    const parent = el.parentElement;
    if (parent && (
      parent.classList.contains('cards-3') ||
      parent.classList.contains('activities-grid') ||
      parent.classList.contains('support-grid') ||
      parent.classList.contains('forwho-grid')
    )) {
      const siblings = Array.from(parent.querySelectorAll('.fade-in'));
      const pos = siblings.indexOf(el);
      el.dataset.delay = pos * 80;
    }
    observer.observe(el);
  });
}

/* =====================================================
   ACTIVE NAV STYLE
   ===================================================== */
(function addActiveNavStyle() {
  const style = document.createElement('style');
  style.textContent = `.nav__link--active { color: var(--orange) !important; background: rgba(232,93,38,0.08); }`;
  document.head.appendChild(style);
})();

/* =====================================================
   FAQ ACCORDION
   ===================================================== */
function initFaq() {
  document.querySelectorAll('.faq-item').forEach(item => {
    const btn = item.querySelector('.faq-q');
    if (!btn) return;
    btn.addEventListener('click', () => {
      const isOpen = item.classList.contains('open');
      document.querySelectorAll('.faq-item.open').forEach(el => el.classList.remove('open'));
      if (!isOpen) item.classList.add('open');
    });
  });
}

/* =====================================================
   IDEA BUILDER — конструктор заявки → WhatsApp
   Никакие данные не сохраняются: формируется текст
   сообщения и открывается чат координатору.
   ===================================================== */
function initIdeaBuilder() {
  const chipsWrap = document.getElementById('ideaChips');
  const chips     = document.querySelectorAll('#ideaChips .idea-chip');
  const textarea  = document.getElementById('ideaText');
  const sendBtn   = document.getElementById('ideaSend');
  const hint      = document.getElementById('ideaHint');
  if (!sendBtn) return;

  // Выбор направления
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      chips.forEach(c => c.classList.remove('idea-chip--active'));
      chip.classList.add('idea-chip--active');
      chipsWrap?.classList.remove('idea-chips--error');
    });
  });

  // Сброс ошибки при вводе текста
  textarea?.addEventListener('input', () => textarea.classList.remove('is-invalid'));

  // Отправка
  sendBtn.addEventListener('click', () => {
    const lang     = document.documentElement.getAttribute('data-lang') || 'ru';
    const selected = document.querySelector('#ideaChips .idea-chip--active');
    const text     = (textarea?.value || '').trim();

    if (!selected) {
      chipsWrap?.classList.add('idea-chips--error');
      flashHint(lang === 'kz' ? '⚠ Алдымен бағытты таңдаңыз' : '⚠ Сначала выберите направление');
      chipsWrap?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }
    if (!text) {
      textarea.classList.add('is-invalid');
      textarea.focus();
      flashHint(lang === 'kz' ? '⚠ Идеяңызды бірер сөзбен жазыңыз' : '⚠ Опишите идею хотя бы в двух словах');
      return;
    }

    const dir = lang === 'kz' ? selected.dataset.dirKz : selected.dataset.dirRu;
    const msg = lang === 'kz'
      ? `Сәлеметсіз бе! 👋\nӨз қауымдастығымды бастағым келеді.\nБағыты: ${dir}\nИдея: ${text}\n— BI Group Көршілік Амбассадорлары сайтынан`
      : `Здравствуйте! 👋\nХочу запустить своё сообщество.\nНаправление: ${dir}\nИдея: ${text}\n— с сайта «Амбассадоры Добрососедства BI Group»`;

    const url = `https://wa.me/${CONFIG.WHATSAPP_COORDINATOR}?text=${encodeURIComponent(msg)}`;
    window.open(url, '_blank', 'noopener');
  });

  // Подсказка-предупреждение с авто-возвратом исходного текста
  let hintTimer = null;
  function flashHint(text) {
    if (!hint) return;
    clearTimeout(hintTimer);
    hint.textContent = text;
    hint.classList.add('idea-hint--error');
    hintTimer = setTimeout(() => {
      hint.classList.remove('idea-hint--error');
      const lang = document.documentElement.getAttribute('data-lang') || 'ru';
      const orig = lang === 'kz'
        ? (hint.getAttribute('data-kz') || '')
        : (hint.getAttribute('data-ru') || '');
      if (orig) hint.innerHTML = orig;
    }, 2800);
  }
}

/* =====================================================
   ACTIVITY CARDS → подставляют направление в конструктор
   ===================================================== */
function initActivityCards() {
  const cards = document.querySelectorAll('.activity-card[data-dir-ru]');
  const chips = document.querySelectorAll('#ideaChips .idea-chip');
  if (!cards.length || !chips.length) return;

  cards.forEach(card => {
    card.addEventListener('click', () => {
      const dir = card.dataset.dirRu;
      chips.forEach(chip => {
        chip.classList.toggle('idea-chip--active', chip.dataset.dirRu === dir);
      });
      document.getElementById('ideaChips')?.classList.remove('idea-chips--error');

      const idea = document.getElementById('idea');
      if (idea) {
        const top = idea.getBoundingClientRect().top + window.scrollY - 70;
        window.scrollTo({ top, behavior: 'smooth' });
      }
      setTimeout(() => document.getElementById('ideaText')?.focus(), 600);
    });
  });
}

/* =====================================================
   HERO SLIDER — ротация фото-слайдов (каркас под фото)
   Чтобы добавить фото: на каждый .rhero__slide повесить
   style="background-image:url('images/hero-1.jpg')"
   ===================================================== */
function initHeroSlider() {
  const slides = document.querySelectorAll('#rheroSlides .rhero__slide');
  const dots   = document.querySelectorAll('#rheroDots .rhero__dot');
  if (slides.length < 2) return;

  let idx = 0, timer = null;
  function go(n) {
    idx = (n + slides.length) % slides.length;
    slides.forEach((s, k) => s.classList.toggle('rhero__slide--active', k === idx));
    dots.forEach((d, k) => d.classList.toggle('rhero__dot--active', k === idx));
  }
  function start() { timer = setInterval(() => go(idx + 1), 5000); }
  function reset() { clearInterval(timer); start(); }

  dots.forEach((d, k) => d.addEventListener('click', () => { go(k); reset(); }));
  start();
}

/* =====================================================
   GALLERY SLIDER — «Жизнь наших дворов» (фото + подписи)
   ===================================================== */
function initGallerySlider() {
  const slides = document.querySelectorAll('#gallerySlides .gslide');
  const dots   = document.querySelectorAll('#galleryDots .g-dot');
  if (slides.length < 2) return;

  let idx = 0, timer = null;
  function go(n) {
    idx = (n + slides.length) % slides.length;
    slides.forEach((s, k) => s.classList.toggle('gslide--active', k === idx));
    dots.forEach((d, k) => d.classList.toggle('g-dot--active', k === idx));
  }
  function start() { timer = setInterval(() => go(idx + 1), 5000); }
  function reset() { clearInterval(timer); start(); }

  dots.forEach((d, k) => d.addEventListener('click', () => { go(k); reset(); }));
  start();
}

/* =====================================================
   ABOUT SLIDER — слайдер фото в блоке «Сообщество»
   Чтобы добавить фото: на каждый .about-slide повесить
   style="background-image:url('images/about-N.jpg')"
   и убрать класс about-slide--empty
   ===================================================== */
function initAboutSlider() {
  const slides = document.querySelectorAll('#aboutSlides .about-slide');
  const dots   = document.querySelectorAll('#aboutDots .about-dot');
  if (slides.length < 2) return;

  let idx = 0, timer = null;
  function go(n) {
    idx = (n + slides.length) % slides.length;
    slides.forEach((s, k) => s.classList.toggle('about-slide--active', k === idx));
    dots.forEach((d, k) => d.classList.toggle('about-dot--active', k === idx));
  }
  function start() { timer = setInterval(() => go(idx + 1), 5000); }
  function reset() { clearInterval(timer); start(); }

  dots.forEach((d, k) => d.addEventListener('click', () => { go(k); reset(); }));
  start();
}
