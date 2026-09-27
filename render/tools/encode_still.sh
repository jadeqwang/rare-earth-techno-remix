#!/usr/bin/env bash
# Still-image video: one rendered frame held for the whole of a track (the extended mix over the title card).
#   tools/encode_still.sh STILL AUDIO OUT [TITLE]
# STILL is a lossless still from tools/render.mjs --png, ideally rendered at 3840x2160: it is area-averaged to
# 1920x1080 once (supersampled halftone), converted with the BT.709 matrix and tagged as such, then repeated.
# Nearly all the bytes are the keyframes, one every 10 s (~1.5 MB of halftone each); the frames between are empty.
# The video ends with the audio, which is re-encoded to AAC at 320 kb/s.
set -euo pipefail
STILL=${1:?still.png}; AUDIO=${2:?audio}; OUT=${3:?out.mp4}; TITLE=${4:-}
ffmpeg -nostdin -loglevel error -y -framerate 24 -i "$STILL" -i "$AUDIO" -map 0:v:0 -map 1:a:0 \
  -vf "scale=1920:1080:flags=area:out_color_matrix=bt709:out_range=tv,format=yuv420p,loop=loop=-1:size=1" -r 24 \
  -c:v libx264 -preset veryslow -tune stillimage -crf 16 -g 240 -profile:v high -level:v 4.1 \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -c:a aac -b:a 320k -shortest ${TITLE:+-metadata title="$TITLE"} -movflags +faststart "$OUT"
ls -la "$OUT"
