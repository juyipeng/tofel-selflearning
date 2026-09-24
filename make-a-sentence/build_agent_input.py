"""Build agent input batches from GLM-OCR layout data (glm_26.X.jsonl).

Each agent batch is a JSON array of questions (compact keys to save tokens):
  {"b": "BS_4月", "st": set_num, "pg": page_in_set, "ix": image_index,
   "p": prompt, "s": sentence (nulls for blanks), "o": options (word list)}
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / 'data'
BATCHES_DIR = DATA / 'agent_batches'

GLM_FILES = [
    ('BS_1月', 'glm_26.1.jsonl'),
    ('BS_2月', 'glm_26.2.jsonl'),
    ('BS_3月', 'glm_26.3.jsonl'),
    ('BS_4月', 'glm_26.4.jsonl'),
    ('BS_5月', 'glm_26.5.jsonl'),
]

BATCH_SIZE = 40


def main():
    entries = []
    for batch, fname in GLM_FILES:
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
                # skip duplicate set 7 of BS_1月 (identical to set 6)
                if batch == 'BS_1月' and rec['set_num'] == 7:
                    continue
                entries.append({
                    'b': batch,
                    'st': rec['set_num'],
                    'pg': rec['page_in_set'],
                    'ix': rec['image_index'],
                    'p': rec['prompt'],
                    's': rec['sentence'],
                    'o': rec['options'],
                })
                n += 1
        print(f'{batch}: {n} questions')

    print(f'Total: {len(entries)} questions')

    # split into batches
    BATCHES_DIR.mkdir(exist_ok=True)
    nb = 0
    for i in range(0, len(entries), BATCH_SIZE):
        chunk = entries[i:i + BATCH_SIZE]
        fn = BATCHES_DIR / f'batch_{nb:03d}.json'
        json.dump(chunk, open(fn, 'w', encoding='utf-8'), ensure_ascii=False)
        nb += 1
    print(f'{nb} batches written to {BATCHES_DIR}')


if __name__ == '__main__':
    main()
