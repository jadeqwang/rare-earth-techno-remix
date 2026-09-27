#!/usr/bin/env bash
# One-time setup for a fresh session: restores /tmp/work so every pipeline and audit script runs without redoing the
# stem separation, pitch tracking, forced alignment or guide extraction. ~3 min (the guides are the slow part).
#   bash pipeline/audit/setup.sh
set -e
cd "$(dirname "$0")/../.."
command -v ffmpeg >/dev/null || (apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ffmpeg)
pip3 install -q numpy scipy soundfile librosa "opencv-python-headless<5" pillow onnxruntime 2>/dev/null
mkdir -p /tmp/work/audit
ffmpeg -nostdin -loglevel error -y -i audio/stems/vocals_kim_vocal_2.flac /tmp/work/vocals.wav      # the vocal stem
cp pipeline/audit/*.py pipeline/audit/vocal_100hz.npz pipeline/audit/align.json /tmp/work/audit/      # pitch/RMS + phones
cp pipeline/audit/lbpcascade_animeface.xml /tmp/work/
ffmpeg -nostdin -loglevel error -y -i out/rare_earth_1080p.mp4 -vn -c:a copy /tmp/work/rel_audio.m4a   # release soundtrack
(cd render && npm install --silent)
python3 pipeline/extract_selects.py                                                                  # guides
echo "ready: see CLAUDE.md for the fix loop"
