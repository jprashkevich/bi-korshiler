#!/usr/bin/env bash
# Скачивает шрифты (SIL OFL) в remotion/public/fonts. Нужно только если папка пустая.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/../remotion/public/fonts"
mkdir -p "$OUT"
base="https://raw.githubusercontent.com/google/fonts/main/ofl"
get() { [ -f "$OUT/$1" ] && echo "⏭  $1" || { echo "⬇️  $1"; curl -sSfL -o "$OUT/$1" "$base/$2"; }; }
get Montserrat.ttf             "montserrat/Montserrat%5Bwght%5D.ttf"
get Inter.ttf                  "inter/Inter%5Bopsz%2Cwght%5D.ttf"
get PlayfairDisplay-Italic.ttf "playfairdisplay/PlayfairDisplay-Italic%5Bwght%5D.ttf"
get Oswald.ttf                 "oswald/Oswald%5Bwght%5D.ttf"
get PTMono-Regular.ttf         "ptmono/PTM55FT.ttf"
get OFL.txt                    "montserrat/OFL.txt"
echo "Готово: $OUT"
