#!/usr/bin/env bash
# Release encode: two-pass H.264 sized under GitHub's 100 MB file limit.
#   tools/encode_release.sh FRAMEDIR AUDIO OUT [VIDEO_KBPS]
# FRAMEDIR holds f_%05d.jpg at 24 fps (from tools/render.mjs --framedir); AUDIO is the sound-design mix.
set -euo pipefail
FRAMES=${1:?framedir}; AUDIO=${2:?audio}; OUT=${3:?out.mp4}; VKBPS=${4:-5500}
N=$(ls "$FRAMES"/f_*.jpg | wc -l)
DUR=$(python3 -c "print($N/24)")
LOG=$(mktemp -d)/x264
ffmpeg -nostdin -loglevel error -y -framerate 24 -i "$FRAMES/f_%05d.jpg" \
  -c:v libx264 -preset slow -profile:v high -b:v ${VKBPS}k -pass 1 -passlogfile "$LOG" -pix_fmt yuv420p -an -f null /dev/null
ffmpeg -nostdin -loglevel error -y -framerate 24 -i "$FRAMES/f_%05d.jpg" -i "$AUDIO" -map 0:v -map 1:a \
  -c:v libx264 -preset slow -profile:v high -b:v ${VKBPS}k -pass 2 -passlogfile "$LOG" -pix_fmt yuv420p \
  -c:a aac -b:a 192k -t "$DUR" -movflags +faststart "$OUT"
ls -la "$OUT"
