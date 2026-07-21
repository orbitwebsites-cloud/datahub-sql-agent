# Demo video pipeline

`DEMO_VIDEO.mp4` (in the repo root) is built entirely offline — **no live screen
capture**. An earlier attempt used `ffmpeg`/`gdigrab` to record the real desktop,
but on a live, shared, interactive session that risks capturing whatever else is
on screen (it did, once, briefly — an unrelated browser window — before this
approach was abandoned in favor of the one below).

Instead, every pixel in the video is rendered from real program output:

1. **`gen_narration.ps1`** — generates narration audio for each beat using
   Windows' built-in `System.Speech` TTS (SAPI5): fully local, free, no API key.
   Writes `beat*.wav` + `durations.json` (exact spoken duration per beat, used
   to pace everything downstream).
2. **`build_audio.sh`** — normalizes the wavs and concatenates them with
   silence gaps (matching the same schedule used in step 3) into
   `narration_master.wav`.
3. **`render_frames.py`** — actually runs `python cli.py "..."` and
   `python -m pytest tests/ -v` as subprocesses and captures their **real**
   stdout (nothing hand-typed or fabricated), then renders each beat as a
   sequence of terminal-styled PNG frames with Pillow (title cards + a
   "typing" reveal of the real output, pausing briefly at each
   `[Result]`/`[Lineage]`/`[Anomaly check]` section so the numbers are
   readable). Writes `frames/` + `frames_list.txt`.
4. `ffmpeg -f concat -i frames_list.txt ...` assembles those frames into a
   silent `video_silent.mp4` (image2/concat demuxer — not a screen capture).
5. `ffmpeg -i video_silent.mp4 -i narration_master.wav ...` muxes the two into
   the final `../DEMO_VIDEO.mp4`.

## Reproduce

```powershell
powershell -ExecutionPolicy Bypass -File gen_narration.ps1
bash build_audio.sh
python render_frames.py
ffmpeg -y -f concat -safe 0 -i frames_list.txt -vsync vfr -pix_fmt yuv420p video_silent.mp4
ffmpeg -y -i video_silent.mp4 -i narration_master.wav -c:v copy -c:a aac -b:a 128k -movflags +faststart ../DEMO_VIDEO.mp4
```

Generated wavs/frames/intermediate mp4s are gitignored (regenerable, and some
are large); only these scripts and `durations.json` are tracked.
