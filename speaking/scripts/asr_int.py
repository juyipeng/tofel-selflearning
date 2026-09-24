#!/usr/bin/env python
"""ASR 转写 108 个「Take an Interview」音频 -> 每个 INT 单元 4 个问题。

用法：python asr_int.py [--limit N]
输出：speaking/data/int.json  ({"units":[{id,title,questions[]}]})
"""
import argparse
import json
import os
import re

os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')
from faster_whisper import WhisperModel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, 'raw-data', 'audio', 'take_an_interview')
OUT = os.path.join(ROOT, 'data', 'int.json')


def extract_topic(q1: str) -> str:
    """从 question_01 的引导语里抽主题，如 "...some questions about your time management habits"."""
    m = re.search(r'about\s+(.+?)[.?!]', q1, re.I)
    if m:
        t = m.group(1).strip()
        # 去掉 "your/their" 之类的开头词，保留核心主题
        t = re.sub(r'^(your|their|the)\s+', '', t, flags=re.I)
        return t
    return ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0, help='只处理前 N 个 INT（0=全部 27）')
    args = ap.parse_args()

    print('loading large-v3 (cuda/int8) ...', flush=True)
    model = WhisperModel('large-v3', device='cuda', compute_type='int8_float16')

    n = min(args.limit or 27, 27)
    units = []
    for i in range(1, n + 1):
        unit = f'INT{i:02d}'
        qs = []
        for j in range(1, 5):
            p = os.path.join(BASE, unit, f'question_{j:02d}.mp3')
            segs, _ = model.transcribe(p, language='en')
            qs.append(' '.join(s.text.strip() for s in segs))
        topic = extract_topic(qs[0]) if qs else ''
        units.append({'id': unit, 'title': topic, 'questions': qs})
        print(f'[{unit}] {topic[:40]:40s} {len(qs)} 题', flush=True)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'units': units}, f, ensure_ascii=False, indent=1)
    print(f'\nSaved {OUT}')


if __name__ == '__main__':
    main()
