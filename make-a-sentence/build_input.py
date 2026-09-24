"""Build questions_input.json from OCR jsonl files.

questions_input.json = flat list of:
  {"batch": "BS_4月", "set_num": 1, "page_in_set": 1, "image_index": 0,
   "strs": [prompt, word1, word2, ...]}

where strs[0] = prompt (first OCR word), strs[1:] = remaining words in OCR order.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / 'data'

# batch name -> OCR jsonl file, in chronological order
BATCHES = [
    ('BS_1月', '26.1.jsonl'),
    ('BS_2月', '26.2.jsonl'),
    ('BS_3月', '26.3.jsonl'),
    ('BS_4月', '26.4.jsonl'),
    ('BS_5月', '26.5.jsonl'),
]


def main():
    out = []
    for batch, fname in BATCHES:
        path = DATA / fname
        if not path.exists():
            print(f'SKIP {batch}: {fname} not found')
            continue
        n = 0
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                words = rec['words']
                if not words:
                    continue
                strs = [w['word'] for w in words]
                out.append({
                    'batch': batch,
                    'set_num': rec['set_num'],
                    'page_in_set': rec['page_in_set'],
                    'image_index': rec['image_index'],
                    'strs': strs,
                })
                n += 1
        print(f'{batch}: {n} questions')

    with open(DATA / 'questions_input.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f'Total: {len(out)} questions')


if __name__ == '__main__':
    main()
