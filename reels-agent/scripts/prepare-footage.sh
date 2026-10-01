#!/usr/bin/env bash
# Нормализует все видео из footage/raw в вертикальные 1080x1920 клипы для Remotion.
#   bash scripts/prepare-footage.sh            # все файлы, по 15 секунд
#   bash scripts/prepare-footage.sh 20         # по 20 секунд
# Короткие ролики зацикливаются, длинные — обрезаются. Звук удаляется (рилсы «тихие»).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
RAW="$ROOT/footage/raw"
OUT="$ROOT/remotion/public/footage"
LEN="${1:-15}"

command -v ffmpeg >/dev/null || { echo "Нужен ffmpeg: brew install ffmpeg / apt install ffmpeg"; exit 1; }
mkdir -p "$OUT"

shopt -s nullglob nocaseglob
files=("$RAW"/*.mp4 "$RAW"/*.mov "$RAW"/*.m4v "$RAW"/*.webm "$RAW"/*.mkv)
if [ ${#files[@]} -eq 0 ]; then
  echo "В $RAW нет видео. Скиньте 5–10 коротких роликов с телефона (работа, дорога, кофе, город)."
  exit 1
fi

n=0
for f in "${files[@]}"; do
  base="$(basename "${f%.*}")"
  # имя: латиница, нижний регистр, дефисы
  slug="$(echo "$base" | iconv -f utf-8 -t ascii//TRANSLIT 2>/dev/null | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g')"
  [ -z "$slug" ] && slug="clip-$n"
  target="$OUT/$slug.mp4"
  if [ -f "$target" ]; then
    echo "⏭  $slug.mp4 уже есть"
    continue
  fi
  echo "🎞  $(basename "$f") → $slug.mp4"
  ffmpeg -hide_banner -loglevel error -stream_loop -1 -i "$f" -t "$LEN" \
    -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p" \
    -an -c:v libx264 -preset fast -crf 18 -movflags +faststart "$target"
  n=$((n+1))
done

echo
echo "Готово. Футажи для batch.json:"
ls -1 "$OUT" | grep -E '\.mp4$' || true
