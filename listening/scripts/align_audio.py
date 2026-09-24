#!/usr/bin/env python
"""Align each passage's stimulus text to whisper word timestamps -> audio range.

Reads: processed/transcript_structured.json, processed/3.22A_full.json
Writes: processed/manifest.json  (passages with audio {start,end})

choose_response passages are split into one passage per question
(each statement is its own short audio clip separated by silence).
"""
import json
import re
from difflib import SequenceMatcher

TS_JSON = "processed/transcript_structured.json"
ASR_JSON = "processed/3.22A_full.json"
OUT = "processed/manifest.json"


def norm_words(text):
    """Normalize text to a list of lowercase alnum tokens (for fuzzy alignment)."""
    # strip speaker labels per line and the audio-missing markers
    text = re.sub(r"(?m)^\s*(Man|Woman|Narrator|Speaker)\s*:\s*", "", text)
    text = text.replace("（音频缺失）", "").replace("(音频缺失)", "")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return text.split()


def main():
    ts = json.load(open(TS_JSON, encoding="utf-8"))
    asr = json.load(open(ASR_JSON, encoding="utf-8"))

    asr_words = []  # {word, start, end}
    for w in asr["words"]:
        asr_words.append({"word": w["word"], "start": w["start"], "end": w["end"]})
    asr_tokens = [re.sub(r"[^a-z0-9\s]", "", w["word"].lower()).strip() for w in asr_words]
    # asr words may become empty after strip; keep aligned via same index

    # --- flatten passages (split choose_response into per-question passages) ---
    passages = []
    pid = 0
    for mod in ts["modules"]:
        for psg in mod["passages"]:
            if psg["type"] == "choose_response":
                for q in psg["questions"]:
                    passages.append({
                        "id": f"m{mod['no']}_q{q['no']:02d}",
                        "module": mod["no"],
                        "section": psg["section"],
                        "type": psg["type"],
                        "stimulus": q["prompt"],
                        "questions": [dict(q)],
                    })
            else:
                passages.append({
                    "id": f"m{mod['no']}_{psg['section'].lower().replace('-', '')}",
                    "module": mod["no"],
                    "section": psg["section"],
                    "type": psg["type"],
                    "stimulus": psg["stimulus"],
                    "questions": [dict(q) for q in psg["questions"]],
                })

    # --- build reference token list with passage tagging ---
    ref_tokens = []
    ref_to_passage = []  # ref token index -> passage index
    passage_range = {}    # passage index -> (r0, r1)
    for pi, p in enumerate(passages):
        toks = norm_words(p["stimulus"])
        r0 = len(ref_tokens)
        ref_tokens.extend(toks)
        r1 = len(ref_tokens)
        ref_to_passage.extend([pi] * len(toks))
        passage_range[pi] = (r0, r1)

    # --- global sequence alignment ---
    sm = SequenceMatcher(None, ref_tokens, asr_tokens, autojunk=False)
    ref_to_asr = [None] * len(ref_tokens)
    for i, j, n in sm.get_matching_blocks():
        for k in range(n):
            ref_to_asr[i + k] = j + k

    # --- per passage: map matched ref tokens -> asr indices -> timestamps ---
    def robust_range(times):
        """Drop outlier words (whisper DTW artifact) by splitting on gaps >3s
        and keeping the larger cluster. Returns (start, end) in seconds."""
        s = sorted(times)
        while len(s) > 1:
            best_gap, best_i = 0.0, -1
            for i in range(1, len(s)):
                gap = s[i][0] - s[i - 1][1]
                if gap > best_gap:
                    best_gap, best_i = gap, i
            if best_gap <= 3.0:
                break
            left_n, right_n = best_i, len(s) - best_i
            s = s[best_i:] if left_n < right_n else s[:best_i]
        return round(min(t[0] for t in s), 2), round(max(t[1] for t in s), 2)

    for pi, p in enumerate(passages):
        r0, r1 = passage_range[pi]
        idxs = [ref_to_asr[r] for r in range(r0, r1) if ref_to_asr[r] is not None]
        matched = len(idxs)
        total = r1 - r0
        if idxs:
            times = [(asr_words[a]["start"], asr_words[a]["end"]) for a in idxs]
            start, end = robust_range(times)
            p["audio"] = {"start": start, "end": end}
        else:
            p["audio"] = None
        p["_match"] = round(matched / max(total, 1), 3)

    # --- report ---
    print(f"passages: {len(passages)}")
    print(f"ref tokens: {len(ref_tokens)}, asr tokens: {len(asr_tokens)}")
    for p in passages:
        a = p["audio"]
        rng = f"{a['start']:7.2f}-{a['end']:7.2f}s" if a else "NO-MATCH"
        print(f"  {p['id']:14s} {p['type']:15s} {rng}  match={p.get('_match')} "
              f"stim={p['stimulus'][:45]!r}")

    # drop debug field
    for p in passages:
        p.pop("_match", None)

    out = {
        "title": ts["title"],
        "date": ts["date"],
        "audio_file": "3.22A_full.wav",
        "audio_duration": round(asr["duration"], 2),
        "passages": passages,
    }
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nSaved {OUT}")


if __name__ == "__main__":
    main()
