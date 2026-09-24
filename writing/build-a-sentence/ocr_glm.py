"""OCR images using local GLM-OCR (via Ollama), preserving the question layout.

Output jsonl records with the layout-based structure:
  {image_file, set_num, page_in_set, image_index,
   prompt, sentence: [null or "word", ...], options: ["word", ...]}

The split (sentence fixed parts vs options) comes from the image LAYOUT
(GLM-OCR reads the middle sentence with blanks and the bottom candidate cards),
not from semantic guessing. Resume-safe.
"""
import json
import re
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).parent
IMAGES = ROOT / 'images'
DATA = ROOT / 'data'

sys.path.insert(0, str(ROOT.parent))   # 仓库根目录
from shared.ocr import ocr_image

# batch name -> (manifest json, output jsonl)
BATCHES = {
    'BS_1月': ('BS_1月_manifest.json', 'glm_26.1.jsonl'),
    'BS_2月': ('BS_2月_manifest.json', 'glm_26.2.jsonl'),
    'BS_3月': ('BS_3月_manifest.json', 'glm_26.3.jsonl'),
    'BS_4月': ('BS_4月_manifest.json', 'glm_26.4.jsonl'),
    'BS_5月': ('BS_5月_manifest.json', 'glm_26.5.jsonl'),
}


def parse(text):
    """Return (prompt, sentence, options) from GLM-OCR transcription."""
    text = re.sub(r'```[a-z]*', '', text)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if not lines:
        return None, None, None
    prompt = lines[0]
    options = lines[-1].split()
    mid = ' '.join(lines[1:-1])
    mid = re.sub(r'_+', ' _BLANK_ ', mid)
    sentence = [None if t == '_BLANK_' else t for t in mid.split()]
    return prompt, sentence, options


def load_done(output_path):
    done = set()
    if output_path.exists():
        with open(output_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    done.add(json.loads(line)['image_file'])
                except json.JSONDecodeError:
                    continue
    return done


def process_batch(batch_name, manifest_name, output_name, limit=None):
    manifest_path = IMAGES / manifest_name
    output_path = DATA / output_name
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    done = load_done(output_path)
    todo = [m for m in manifest if m['image_file'] not in done]
    if limit is not None:
        todo = todo[:limit]

    print(f'[{batch_name}] total={len(manifest)}, done={len(done)}, todo={len(todo)}')

    with open(output_path, 'a', encoding='utf-8') as out:
        for i, m in enumerate(todo):
            img_path = ROOT / m['image_file']
            if not img_path.exists():
                print(f'  [{i+1}/{len(todo)}] MISSING: {m["image_file"]}')
                continue

            text = ocr_image(img_path, retries=2)   # 组句题侧原为 2 次重试
            if text is None:
                continue
            prompt, sentence, options = parse(text)
            if prompt is None:
                print(f'  [{i+1}/{len(todo)}] EMPTY: {m["image_file"]}')
                continue

            record = {
                'image_file': m['image_file'],
                'set_num': m['set_num'],
                'page_in_set': m['page_in_set'],
                'image_index': m['image_index'],
                'prompt': prompt,
                'sentence': sentence,
                'options': options,
                'raw': text,
            }
            out.write(json.dumps(record, ensure_ascii=False) + '\n')
            out.flush()

            if (i + 1) % 10 == 0 or i == len(todo) - 1:
                print(f'  [{i+1}/{len(todo)}] done (last: {m["image_file"]})')

    print(f'[{batch_name}] complete.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=None, help='max images per batch')
    args = parser.parse_args()

    DATA.mkdir(exist_ok=True)
    for batch_name, (manifest_name, output_name) in BATCHES.items():
        if not (IMAGES / manifest_name).exists():
            print(f'SKIP {batch_name}: manifest not found')
            continue
        process_batch(batch_name, manifest_name, output_name, args.limit)


if __name__ == '__main__':
    main()
