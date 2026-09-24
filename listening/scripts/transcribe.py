#!/usr/bin/env python
"""Transcribe audio with faster-whisper large-v3 (GPU), with word-level timestamps.

Usage:
  KMP_DUPLICATE_LIB_OK=TRUE python transcribe.py <audio_path> <out_json> [--model large-v3] [--language en]
"""
import argparse
import json
import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from faster_whisper import WhisperModel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("out_json")
    ap.add_argument("--model", default="large-v3")
    ap.add_argument("--language", default="en")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--compute_type", default="int8_float16")
    args = ap.parse_args()

    print(f"Loading {args.model} on {args.device} ({args.compute_type}) ...", flush=True)
    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)

    print("Transcribing ...", flush=True)
    segments, info = model.transcribe(
        args.audio,
        language=args.language,
        word_timestamps=True,
        vad_filter=True,
        beam_size=5,
    )

    result = {"language": info.language, "duration": info.duration,
              "segments": [], "words": []}
    for seg in segments:
        seg_words = []
        for w in seg.words:
            seg_words.append({"word": w.word, "start": round(w.start, 3),
                              "end": round(w.end, 3), "prob": round(w.probability, 3)})
            result["words"].append(seg_words[-1])
        result["segments"].append({
            "id": seg.id, "start": round(seg.start, 3), "end": round(seg.end, 3),
            "text": seg.text.strip(), "words": seg_words,
        })
        print(f"[{seg.start:7.2f} -> {seg.end:7.2f}] {seg.text.strip()}", flush=True)

    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"\nSaved {args.out_json} ({len(result['segments'])} segments, "
          f"{len(result['words'])} words)")


if __name__ == "__main__":
    main()
