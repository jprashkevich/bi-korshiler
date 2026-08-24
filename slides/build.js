const pptxgen = require("pptxgenjs");

const BG      = "101A3D";  // глубокий тёмно-синий (фирменный navy)
const CARD    = "1A2A5C";
const WHITE   = "FFFFFF";
const MUTED   = "9AA6C9";
const CYAN    = "00C2FF";

const ROWS = [
  { name: "Добрососедство",        n: 3548, p: "30%", c: "00C2FF",
    d: "Соседские встречи, праздники двора, чаепития, пицца-пати" },
  { name: "Семья",                 n: 3251, p: "28%", c: "F2A33C",
    d: "163 мероприятия, ~20 человек на событие — самый плотный формат" },
  { name: "Longevity",             n: 1769, p: "15%", c: "4CD3A5",
    d: "Активности для здоровья и долголетия, в основном для старшего возраста" },
  { name: "Физическая активность", n: 1481, p: "13%", c: "6E8BE8",
    d: "Спортивные игры, зарядки, дворовые турниры" },
  { name: "Самореализация",        n: 1143, p: "10%", c: "B07FE8",
    d: "Мастер-классы и творчество: «Очумелые ручки», сборка пазлов" },
  { name: "Эко и благоустройство", n:  441, p:  "4%", c: "7C8AC0",
    d: "Субботники, озеленение — нишевый формат" },
];

const TOTAL = ROWS.reduce((s, r) => s + r.n, 0);
const fmt = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, " ");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";               // 13.333 x 7.5
const slide = pres.addSlide();
slide.background = { color: BG };

/* ---------- Заголовок ---------- */
slide.addText("Что реально «притягивает» жителей", {
  x: 0.55, y: 0.38, w: 9.5, h: 0.62, margin: 0,
  fontFace: "Calibri", fontSize: 34, bold: true, color: WHITE,
});
slide.addText("Распределение охвата по форматам активностей", {
  x: 0.57, y: 1.02, w: 9.5, h: 0.34, margin: 0,
  fontFace: "Calibri", fontSize: 14.5, color: MUTED,
});

/* ---------- Кольцевая диаграмма ---------- */
const CH = { x: 0.35, y: 1.55, w: 4.85, h: 4.45 };
slide.addChart(
  pres.ChartType.doughnut,
  [{ name: "Участники", labels: ROWS.map(r => r.name), values: ROWS.map(r => r.n) }],
  {
    ...CH,
    chartColors: ROWS.map(r => r.c),
    holeSize: 58,
    showLegend: false,
    showTitle: false,
    showPercent: true,
    showValue: false,
    dataLabelPosition: "ctr",
    dataLabelColor: "0E1733",
    dataLabelFontFace: "Calibri",
    dataLabelFontSize: 12,
    dataLabelFontBold: true,
    dataBorder: { pt: 2.5, color: BG },
    firstSliceAng: 0,
  }
);
// центр кольца
slide.addText(fmt(TOTAL), {
  x: CH.x + CH.w / 2 - 1.0, y: CH.y + CH.h / 2 - 0.44, w: 2.0, h: 0.52, margin: 0,
  align: "center", fontFace: "Calibri", fontSize: 30, bold: true, color: WHITE,
});
slide.addText("участника", {
  x: CH.x + CH.w / 2 - 1.0, y: CH.y + CH.h / 2 + 0.08, w: 2.0, h: 0.28, margin: 0,
  align: "center", fontFace: "Calibri", fontSize: 12.5, color: MUTED,
});

/* ---------- Рейтинг форматов ---------- */
const LX = 5.55, LW = 7.25, RH = 0.70, GAP = 0.045;
let y = 1.58;
ROWS.forEach(r => {
  slide.addShape(pres.ShapeType.ellipse, {
    x: LX, y: y + 0.09, w: 0.17, h: 0.17, fill: { color: r.c },
  });
  slide.addText(r.name, {
    x: LX + 0.32, y: y - 0.02, w: 4.35, h: 0.32, margin: 0,
    fontFace: "Calibri", fontSize: 15, bold: true, color: WHITE,
  });
  slide.addText(
    [
      { text: fmt(r.n), options: { fontSize: 15, bold: true, color: WHITE } },
      { text: "   " + r.p, options: { fontSize: 15, bold: true, color: r.c } },
    ],
    { x: LX + 4.7, y: y - 0.02, w: LW - 4.7, h: 0.32, margin: 0,
      align: "right", fontFace: "Calibri" }
  );
  slide.addText(r.d, {
    x: LX + 0.32, y: y + 0.28, w: LW - 0.32, h: 0.3, margin: 0,
    fontFace: "Calibri", fontSize: 11.5, color: MUTED,
  });
  y += RH + GAP;
});

/* ---------- Вывод ---------- */
slide.addShape(pres.ShapeType.roundRect, {
  x: 0.55, y: 6.32, w: 12.25, h: 0.78, rectRadius: 0.1,
  fill: { color: CARD },
});
slide.addText(
  [
    { text: "Массовость даёт добрососедство, плотность — семья:", options: { bold: true, color: CYAN } },
    { text: "  3 251 участник всего за 163 мероприятия — около 20 человек на каждое событие, " +
            "тогда как эко-повестка остаётся нишевой (4%).", options: { color: "D6DDF2" } },
  ],
  { x: 0.85, y: 6.32, w: 11.65, h: 0.78, margin: 0,
    valign: "middle", fontFace: "Calibri", fontSize: 13 }
);

slide.addNotes(
  "Топ-2 формата (добрососедство и семья) дают 58% всего охвата — " +
  "почти 6 800 участий. Семья при этом самый эффективный формат по плотности: " +
  "~20 человек на мероприятие против среднего по остальным направлениям. " +
  "Эко и благоустройство — 4%, требует отдельной механики вовлечения."
);

pres.writeFile({ fileName: "big-life-formats.pptx" }).then(f => console.log("saved:", f));
