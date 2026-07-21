#!/usr/bin/env bash
# Builds narration_master.wav: matches run_demo.ps1's exact schedule
# (5s preroll, then per-beat speech + post-narration buffer, in order)
# so it can be muxed onto the silently-recorded video afterward.
set -e
cd "$(dirname "$0")"

norm() {
  ffmpeg -y -i "$1.wav" -ar 44100 -ac 1 -c:a pcm_s16le "norm_$1.wav" -loglevel error
}

silence() {
  ffmpeg -y -f lavfi -i anullsrc=r=44100:cl=mono -t "$1" -c:a pcm_s16le "sil_$2.wav" -loglevel error
}

norm beat1_intro
norm beat2_normal
norm beat3_anomaly
norm beat4_free
norm beat5_close

silence 5  preroll
silence 2  b1
silence 8  b2
silence 12 b3
silence 2  b4
silence 5  b5

cat > concat_list.txt <<EOF
file 'sil_preroll.wav'
file 'norm_beat1_intro.wav'
file 'sil_b1.wav'
file 'norm_beat2_normal.wav'
file 'sil_b2.wav'
file 'norm_beat3_anomaly.wav'
file 'sil_b3.wav'
file 'norm_beat4_free.wav'
file 'sil_b4.wav'
file 'norm_beat5_close.wav'
file 'sil_b5.wav'
EOF

ffmpeg -y -f concat -safe 0 -i concat_list.txt -c copy narration_master.wav -loglevel error

ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 narration_master.wav
