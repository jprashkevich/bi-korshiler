#!/usr/bin/env python3
"""
Перевод растровых QR бронирования в вектор.

Зачем: на плакате код печатается 100+ мм, а исходный PNG — 1196 px.
Браузер растягивал его с интерполяцией, края модулей размывались, и часть
кодов переставала читаться частью декодеров. В SVG модуль остаётся модулем
при любом размере.

viewBox = N×N модулей, белого поля внутри нет — quiet zone задаёт макет
(белая подложка вокруг). Так размер бокса в CSS равен размеру самого кода.

shape-rendering намеренно не задаётся: crispEdges притягивает края модулей
к пикселям устройства, и при нецелом модуле (37 шт. на 103 мм) соседние
модули отличаются по ширине на пиксель — часть декодеров на этом сбоит.

    pip install pillow
    python3 build/qr_png_to_svg.py
"""
import pathlib
from PIL import Image

QR_DIR = pathlib.Path(__file__).resolve().parent.parent / 'assets' / 'qr'


def module_grid(img: Image.Image):
    """Возвращает (N, module_px) для изображения, обрезанного ровно по коду."""
    g = img.convert('L')
    w, _ = g.size
    px = g.load()
    # белое поле внутри файла — 9% стороны, снимаем его
    pad = round(w * 0.09 / 1.18)
    left, size = pad, w - 2 * pad
    # верхний левый поисковый шаблон — ровно 7 модулей
    y = left + max(1, size // 100)
    x = left
    while x < left + size and px[x, y] >= 128:
        x += 1
    start = x
    while x < left + size and px[x, y] < 128:
        x += 1
    run = x - start
    if run <= 0:
        raise ValueError('не найден поисковый шаблон')
    n = round(size * 7 / run)
    return n, size / n, start, y


def to_svg(path: pathlib.Path) -> str:
    img = Image.open(path)
    g = img.convert('L')
    w, _ = g.size
    px = g.load()
    pad = round(w * 0.09 / 1.18)
    n, mod, ox, _ = module_grid(img)
    rects = []
    for r in range(n):
        c = 0
        while c < n:
            if px[int(ox + (c + .5) * mod), int(ox + (r + .5) * mod)] < 128:
                start = c
                while c < n and px[int(ox + (c + .5) * mod), int(ox + (r + .5) * mod)] < 128:
                    c += 1
                rects.append(f'M{start} {r}h{c - start}v1h-{c - start}z')
            else:
                c += 1
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" '
            f'width="100%" height="100%" shape-rendering="crispEdges" role="img" aria-label="QR">'
            f'<path fill="currentColor" d="{"".join(rects)}"/></svg>'), n


def main() -> int:
    files = sorted(QR_DIR.glob('*.png'))
    for path in files:
        svg, n = to_svg(path)
        out = path.with_suffix('.svg')
        out.write_text(svg, encoding='utf-8')
        print(f'✓ {path.name}  →  {out.name}  ({n}×{n} модулей, {len(svg)} байт)')
    print(f'\nГотово: {len(files)} шт.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
