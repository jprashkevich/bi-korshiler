#!/usr/bin/env python3
"""
Подготовка QR-кодов для плакатов Yourt.

Исходники приходят одним шаблоном 800×1050: логотип yourt., название
пространства, сам QR, двуязычная подпись. Для плаката нужен только
QR-модуль — остальное рисует макет. Скрипт вырезает квадрат QR по
границам чёрных пикселей, добавляет белое поле (quiet zone 9%)
и удваивает разрешение — на печати выходит ~540 dpi.

    pip install pillow
    python3 build/prep_qr.py <папка-с-исходниками> [<папка-назначения>]

По умолчанию назначение — posters/assets/qr.
Имя файла qr_booking_<Name>.png превращается в <Name>.png; этот <Name>
и есть id пространства в build/content.mjs.
"""
import sys
import pathlib
from PIL import Image

PAD_RATIO = 0.09        # белое поле вокруг QR, доля стороны
SCAN_TOP, SCAN_BOTTOM = 240, 830   # полоса поиска QR в шаблоне 800×1050


def crop_qr(path: pathlib.Path) -> Image.Image:
    src = Image.open(path).convert('L')
    w, _ = src.size
    px = src.load()

    # горизонтальные границы берём по строкам заведомо внутри QR
    min_x, max_x = w, 0
    for y in range(SCAN_TOP + 80, SCAN_BOTTOM - 130):
        for x in range(w):
            if px[x, y] < 128:
                min_x = min(min_x, x)
                max_x = max(max_x, x)
    if max_x <= min_x:
        raise ValueError(f'{path.name}: QR не найден')

    side = max_x - min_x + 1
    # верхняя граница — первая тёмная строка внутри найденной колонки
    min_y = next(y for y in range(SCAN_TOP, SCAN_BOTTOM)
                 if any(px[x, y] < 128 for x in range(min_x, max_x + 1)))

    qr = Image.open(path).crop((min_x, min_y, min_x + side, min_y + side))
    pad = round(side * PAD_RATIO)
    canvas = Image.new('L', (side + 2 * pad,) * 2, 255)
    canvas.paste(qr.convert('L'), (pad, pad))
    return canvas.resize((canvas.width * 2, canvas.height * 2), Image.NEAREST)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    src_dir = pathlib.Path(sys.argv[1])
    dst_dir = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 \
        else pathlib.Path(__file__).resolve().parent.parent / 'assets' / 'qr'
    dst_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in src_dir.glob('*.png') if not p.name.startswith('._'))
    for path in files:
        out_name = path.name.replace('qr_booking_', '')
        out_path = dst_dir / out_name
        crop_qr(path).save(out_path)
        print(f'✓ {path.name}  →  {out_path.relative_to(dst_dir.parent.parent)}')
    print(f'\nГотово: {len(files)} шт. Проверьте, что id есть в build/content.mjs.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
