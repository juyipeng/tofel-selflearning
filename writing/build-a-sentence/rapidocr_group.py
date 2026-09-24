"""Run RapidOCR detection to determine option card grouping (spacing-based).

The GLM-OCR gives options as individual words; the original question shows them
as CARDS (close words = one card, far words = separate cards). RapidOCR's
detection boxes reveal the card boundaries. This script groups each question's
GLM-OCR option words into cards and saves the result (resume-safe).

Output: data/rapidocr_cards.jsonl, one record per question:
  {image_file, cards: [["word",...], ...]}  (cards in display order)
"""
import json
import re
import time
from pathlib import Path
from rapidocr_onnxruntime import RapidOCR

ROOT = Path(__file__).parent
DATA = ROOT / 'data'

GLM_FILES = [
    ('BS_1月', 'glm_26.1.jsonl'),
    ('BS_2月', 'glm_26.2.jsonl'),
    ('BS_3月', 'glm_26.3.jsonl'),
    ('BS_4月', 'glm_26.4.jsonl'),
    ('BS_5月', 'glm_26.5.jsonl'),
]

eng = RapidOCR()


def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def detect_cards(img_path):
    """Return the bottom-row card texts (concatenated), in left-to-right order."""
    res, _ = eng(img_path)
    bottom = [r for r in res if min(p[1] for p in r[0]) > 900]
    bottom.sort(key=lambda r: min(p[0] for p in r[0]))
    return [r[1] for r in bottom]


def group_words(words, cards):
    """Split `words` (display order) into cards using cumulative char alignment."""
    if not cards or not words:
        return [words] if words else []
    wc = []
    c = 0
    for w in words:
        c += len(norm(w))
        wc.append(c)
    cc = []
    c = 0
    for cd in cards:
        c += len(norm(cd))
        cc.append(c)
    groups = []
    last = 0
    for b in cc[:-1]:
        idx = min(range(len(wc)), key=lambda i: abs(wc[i] - b))
        idx = max(idx, last)
        groups.append(words[last:idx + 1])
        last = idx + 1
    groups.append(words[last:])
    return [g for g in groups if g]


def load_done(out_path):
    done = set()
    if out_path.exists():
        for line in open(out_path, encoding='utf-8'):
            line = line.strip()
            if line:
                try:
                    done.add(json.loads(line)['image_file'])
                except (json.JSONDecodeError, KeyError):
                    continue
    return done


def main():
    out_path = DATA / 'rapidocr_cards.jsonl'
    done = load_done(out_path)

    # collect all valid glm records
    records = []
    for batch, fname in GLM_FILES:
        p = DATA / fname
        if not p.exists():
            continue
        for line in open(p, encoding='utf-8'):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec['image_file'] in done:
                continue
            sent = rec['sentence']
            opts = rec['options']
            if not sent or not opts or sum(1 for x in sent if x is None) == 0:
                continue  # skip broken
            if any(re.search(r'_+', str(w)) for w in opts):
                continue
            records.append(rec)

    print(f'todo {len(records)} questions')

    with open(out_path, 'a', encoding='utf-8') as out:
        for i, rec in enumerate(records):
            img = ROOT / rec['image_file']
            if not img.exists():
                continue
            try:
                cards = detect_cards(img)
                grouped = group_words(rec['options'], cards)
            except Exception as e:
                print(f'  {rec["image_file"]} FAILED: {e}')
                continue
            out.write(json.dumps({'image_file': rec['image_file'], 'cards': grouped},
                                 ensure_ascii=False) + '\n')
            out.flush()
            if (i + 1) % 50 == 0:
                print(f'  [{i+1}/{len(records)}] done')

    print('complete.')


if __name__ == '__main__':
    main()
