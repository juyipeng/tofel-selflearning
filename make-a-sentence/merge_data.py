"""Build questions_final.json from questions_input.json + parsed_raw.json.

Uses the agent's parse DIRECTLY as ground truth. The earlier "largest gap in OCR
top coordinate" rule (recompute_split.py) was broken — it mislabeled sentence
parts as options for 486/488 questions. The agent's parse already encodes the
correct split: `s` = sentence structure (null = blank), `a` = answers (removed
words, in correct fill order).

This script only adds the two pieces the agent does not provide:
  * prompt (from strs[0])
  * options (answers re-ordered by OCR position = the natural scrambled order)
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / 'data'

# batch name -> OCR jsonl file (chronological order)
BATCHES = [
    ('BS_1月', '26.1.jsonl'),
    ('BS_2月', '26.2.jsonl'),
    ('BS_3月', '26.3.jsonl'),
    ('BS_4月', '26.4.jsonl'),
    ('BS_5月', '26.5.jsonl'),
]


def normalize(s):
    s = s.lower().strip()
    s = re.sub(r'[^a-z0-9 ]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def get_sa(p):
    """Return (sentence, answers) from either parsed_raw format."""
    if 's' in p:
        return p['s'], p['a']
    return p['sentence'], p['answers']


def load_raw():
    """dict[(batch, set_num, page_in_set, image_index)] -> list of OCR words (order kept)."""
    raw = {}
    for batch, fname in BATCHES:
        path = DATA / fname
        if not path.exists():
            continue
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                key = (batch, rec['set_num'], rec['page_in_set'], rec['image_index'])
                raw[key] = [w['word'] for w in rec['words'][1:]]
    return raw


def main():
    raw = load_raw()
    q_input = json.load(open(DATA / 'questions_input.json', 'r', encoding='utf-8'))
    parsed = json.load(open(DATA / 'parsed_raw.json', 'r', encoding='utf-8'))
    assert len(q_input) == len(parsed), f'{len(q_input)} != {len(parsed)}'

    new_data = {}
    missing = 0

    for inp, p in zip(q_input, parsed):
        s, a = get_sa(p)

        key = (inp['batch'], inp['set_num'], inp['page_in_set'], inp['image_index'])
        raw_words = raw.get(key)
        if raw_words is None:
            missing += 1
            continue
        raw_norm = [normalize(w) for w in raw_words]

        def ocr_pos(ans):
            """OCR index of an answer (for scrambled options order)."""
            n_a = normalize(ans)
            for i, nw in enumerate(raw_norm):
                if nw == n_a:
                    return i
            pos = [i for i, nw in enumerate(raw_norm) if nw and nw in n_a]
            if pos:
                return min(pos)
            for i, nw in enumerate(raw_norm):
                if n_a and n_a in nw:
                    return i
            return len(raw_words)

        options = sorted(a, key=ocr_pos)

        q = {
            'prompt': inp['strs'][0],
            'sentence': s,
            'options': options,
            'answers': a,
        }

        b = inp['batch']
        sk = f"set_{inp['set_num']:02d}"
        if b not in new_data:
            new_data[b] = {'name': f'{b} 真题', 'sets': {}}
        if sk not in new_data[b]['sets']:
            new_data[b]['sets'][sk] = {'name': f"第 {inp['set_num']} 套", 'questions': []}
        new_data[b]['sets'][sk]['questions'].append(q)

    with open(DATA / 'questions_final.json', 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

    nq = sum(len(s['questions']) for b in new_data for s in new_data[b]['sets'].values())
    mismatches = 0
    for b in new_data:
        for s in new_data[b]['sets'].values():
            for q in s['questions']:
                n_null = sum(1 for x in q['sentence'] if x is None)
                if n_null != len(q['answers']) or n_null != len(q['options']):
                    mismatches += 1
    print(f'Merged: {nq} questions, {missing} missing raw coords, {mismatches} null/answer mismatches')


if __name__ == '__main__':
    main()
