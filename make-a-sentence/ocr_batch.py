"""Batch OCR all extracted images using Alibaba Cloud OCR, store results as jsonl.

Usage:
    python ocr_batch.py                 # process all images (resume-safe)
    python ocr_batch.py --limit 10      # process only first 10 images
    python ocr_batch.py --reset         # ignore existing results, restart from scratch
"""
import json
import base64
import ssl
import time
import sys
import argparse
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).parent
IMAGES = ROOT / 'images'
DATA = ROOT / 'data'

sys.path.insert(0, str(ROOT.parent))   # 仓库根目录
from shared.config import get_secret

REQUEST_URL = 'https://tysbgpu.market.alicloudapi.com/api/predict/ocr_general'
APPCODE = get_secret('aliyun_ocr_appcode')   # config.json 或环境变量 ALIYUN_OCR_APPCODE

context = ssl._create_unverified_context()

# Map: batch name -> (manifest json, output jsonl)
BATCHES = {
    '26.1': ('BS_1月_manifest.json', '26.1.jsonl'),
    '26.2': ('BS_2月_manifest.json', '26.2.jsonl'),
    '26.3': ('BS_3月_manifest.json', '26.3.jsonl'),
    '26.4': ('BS_4月_manifest.json', '26.4.jsonl'),
    '26.5': ('BS_5月_manifest.json', '26.5.jsonl'),
}


def ocr_image(img_path, retries=3):
    """Call OCR API for a single image, return the 'ret' list."""
    with open(img_path, 'rb') as f:
        data = f.read()
    enc = base64.b64encode(data).decode('utf-8')

    body = {
        'image': enc,
        'configure': {
            'min_size': 16,
            'output_prob': True,
            'output_keypoints': False,
            'skip_detection': False,
            'dir_assure': False,
        },
    }
    headers = {
        'Authorization': 'APPCODE %s' % APPCODE,
        'Content-Type': 'application/json; charset=UTF-8',
    }

    for attempt in range(retries):
        try:
            req = Request(REQUEST_URL, json.dumps(body).encode('utf-8'), headers)
            r = urlopen(req, context=context, timeout=60)
            resp = json.loads(r.read().decode('utf-8'))
            if resp.get('success'):
                return resp.get('ret', [])
            else:
                print(f'  API not success: {resp}')
                return []
        except (HTTPError, URLError, Exception) as e:
            if attempt < retries - 1:
                wait = 2 ** attempt
                print(f'  error ({e}), retry in {wait}s...')
                time.sleep(wait)
            else:
                print(f'  FAILED after {retries} tries: {e}')
                return None
    return None


def load_done(output_path):
    """Return set of already-processed image_file paths."""
    done = set()
    if output_path.exists():
        with open(output_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    done.add(rec['image_file'])
                except json.JSONDecodeError:
                    continue
    return done


def process_batch(batch_name, manifest_name, output_name, limit=None, reset=False):
    manifest_path = IMAGES / manifest_name
    output_path = DATA / output_name

    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    done = set() if reset else load_done(output_path)

    todo = [m for m in manifest if m['image_file'] not in done]
    if limit is not None:
        todo = todo[:limit]

    print(f'[{batch_name}] total={len(manifest)}, done={len(done)}, todo={len(todo)}')

    # Append mode (unless reset)
    mode = 'w' if reset else 'a'
    with open(output_path, mode, encoding='utf-8') as out:
        for i, m in enumerate(todo):
            img_path = ROOT / m['image_file']
            if not img_path.exists():
                print(f'  [{i+1}/{len(todo)}] MISSING: {m["image_file"]}')
                continue

            ret = ocr_image(img_path)
            if ret is None:
                print(f'  [{i+1}/{len(todo)}] OCR FAILED: {m["image_file"]} (not saved)')
                continue

            record = {
                'image_file': m['image_file'],
                'set_num': m['set_num'],
                'page_in_set': m['page_in_set'],
                'image_index': m['image_index'],
                'source_page': m['source_page'],
                'words': ret,
            }
            out.write(json.dumps(record, ensure_ascii=False) + '\n')
            out.flush()

            if (i + 1) % 10 == 0 or i == len(todo) - 1:
                print(f'  [{i+1}/{len(todo)}] done (last: {m["image_file"]})')

            time.sleep(0.2)  # gentle rate limit

    print(f'[{batch_name}] complete.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=None, help='max images per batch')
    parser.add_argument('--reset', action='store_true', help='ignore existing results')
    args = parser.parse_args()

    DATA.mkdir(exist_ok=True)
    for batch_name, (manifest_name, output_name) in BATCHES.items():
        if not (IMAGES / manifest_name).exists():
            print(f'SKIP {batch_name}: manifest not found')
            continue
        process_batch(batch_name, manifest_name, output_name, args.limit, args.reset)


if __name__ == '__main__':
    main()
