"""OCR all reading images using local GLM-OCR (via Ollama).

Simple transcribe prompt — structure is parsed downstream in Python (the
0.9B model gets worse with structured prompts). Resume-safe: images already
present in data/ocr.jsonl are skipped, so re-running re-attempts only the
missed/failed ones (失败重跑).
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
IMAGES = ROOT / 'images'
DATA = ROOT / 'data'
MANIFEST = IMAGES / 'manifest.json'
OUTPUT = DATA / 'ocr.jsonl'

sys.path.insert(0, str(ROOT.parent))   # 仓库根目录
from shared.ocr import ocr_image as _ocr_image


def ocr_image(img_path, retries=3):
    """reading 侧约定：去掉首尾空白；返回 None 表示重试耗尽。"""
    return _ocr_image(img_path, retries=retries, strip=True)


def load_done():
    done = set()
    if OUTPUT.exists():
        with open(OUTPUT, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    done.add(json.loads(line)['image_file'])
                except (json.JSONDecodeError, KeyError):
                    continue
    return done


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=None, help='max images this run')
    args = parser.parse_args()

    DATA.mkdir(exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    done = load_done()
    todo = [m for m in manifest if m['image_file'] not in done]
    if args.limit is not None:
        todo = todo[:args.limit]

    print(f'total={len(manifest)} done={len(done)} todo={len(todo)}')
    failed = []
    t0 = time.time()
    with open(OUTPUT, 'a', encoding='utf-8') as out:
        for i, m in enumerate(todo):
            img_path = ROOT / m['image_file']
            if not img_path.exists():
                failed.append(m['image_file'])
                continue
            raw = ocr_image(img_path)
            if raw is None or raw == '':
                failed.append(m['image_file'])
                print(f'  [{i+1}/{len(todo)}] FAILED: {m["image_file"]}')
                continue
            rec = {
                'image_file': m['image_file'],
                'set': m['set'],
                'module': m['module'],
                'index': m['index'],
                'raw': raw,
            }
            out.write(json.dumps(rec, ensure_ascii=False) + '\n')
            out.flush()
            if (i + 1) % 10 == 0 or i == len(todo) - 1:
                el = time.time() - t0
                print(f'  [{i+1}/{len(todo)}] elapsed={el:.0f}s (last {m["image_file"]})')

    print(f'\nDone. failed={len(failed)}')
    if failed:
        with open(DATA / 'ocr_failed.txt', 'w', encoding='utf-8') as f:
            f.write('\n'.join(failed) + '\n')
        print('failed list -> data/ocr_failed.txt')


if __name__ == '__main__':
    main()
