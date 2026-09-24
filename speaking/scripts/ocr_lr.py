#!/usr/bin/env python
"""OCR 19 个「Listen and Repeat」主题页 -> 标题 + 场景 + 7 句。

用法：python ocr_lr.py [--limit N]
输出：speaking/data/lr.json  ({"topics":[{id,title,scenario,sentences[]}]})
"""
import argparse
import base64
import io
import json
import re
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / '新托福口语7月回顾.pdf'
DATA = ROOT / 'data'
OUT = DATA / 'lr.json'

OLLAMA = 'http://localhost:11434/api/generate'
MODEL = 'glm-ocr:q8_0'
OCR_PROMPT = 'Transcribe all the text in this image, preserving line breaks and layout.'

TXL = 'C:/texlive/2024/bin/windows'

# 19 个主题标题（顺序 = PDF 第 6~24 页 = LR01~LR19），来自 PDF 文字层目录
TITLES = [
    "Wall Painting Training", "Community Garden Training", "Woodworking Simple Steps",
    "Class Registration Training", "Handling Sensitive Library Materials",
    "Science Project Presentations", "Supporting Learners in a Yoga Studio",
    "Making a Clay Bowl", "Arranging Flowers", "Botanical Garden Care",
    "Baking Bread", "Media Production Studio", "Watercolor Painting",
    "Career Fair Services", "Cultural Festival Guide", "Preparing a Latte",
    "Art Gallery Guide", "Online Learning Platform", "Repairing a Bicycle Tire",
]


def ocr(img_path: Path) -> str:
    im = Image.open(img_path).convert('RGB')
    w, h = im.size
    if w > 1600:
        im = im.resize((1600, max(1, int(h * 1600 / w))))
    buf = io.BytesIO()
    im.save(buf, format='JPEG')
    b64 = base64.b64encode(buf.getvalue()).decode()
    body = {'model': MODEL, 'prompt': OCR_PROMPT, 'images': [b64], 'stream': False}
    req = Request(OLLAMA, json.dumps(body).encode('utf-8'), {'Content-Type': 'application/json'})
    return json.loads(urlopen(req, timeout=600).read().decode('utf-8')).get('response', '')


def render_page(pageno: int, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([f'{TXL}/pdftoppm', '-png', '-r', '120', '-f', str(pageno), '-l', str(pageno),
                    str(PDF), str(out_dir / 'page')], check=True, capture_output=True)
    p = out_dir / f'page-{pageno:02d}.png'
    return p


def parse_page(text: str) -> dict:
    lines = [l.strip() for l in text.split('\n')]
    lines = [l for l in lines if l]

    scenario = ''
    sentences = []

    # 定位 Scenario 段 和 LISTEN AND REPEAT 段
    scen_i = lr_i = None
    for i, l in enumerate(lines):
        if scen_i is None and re.match(r'^Scenario\b', l, re.I):
            scen_i = i
        if re.search(r'LISTEN\s+AND\s+REPEAT', l, re.I):
            lr_i = i
            break

    if scen_i is not None:
        # 情况1：Scenario 与正文同行  "Scenario A trainer is teaching..."
        m = re.match(r'^Scenario\s*[:：]?\s*(.+)$', lines[scen_i], re.I)
        if m and m.group(1):
            scenario = m.group(1).strip()
        # 情况2：Scenario 单独成行，正文在下一行到 LISTEN 之间
        elif lr_i is not None and lr_i > scen_i + 1:
            scenario = ' '.join(lines[scen_i + 1:lr_i]).strip()

    # 句子：LISTEN AND REPEAT 之后，形如 "1. xxx"
    start = lr_i if lr_i is not None else (scen_i if scen_i is not None else 0)
    for l in lines[start + 1:]:
        m = re.match(r'^(\d+)[\.\)]\s*(.+)$', l)
        if m:
            sentences.append(m.group(2).strip())

    return {'scenario': scenario, 'sentences': sentences}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0, help='只处理前 N 页（0=全部 19 页）')
    args = ap.parse_args()

    DATA.mkdir(parents=True, exist_ok=True)
    tmp = ROOT / 'raw-data' / 'rendered'
    tmp.mkdir(parents=True, exist_ok=True)

    n = min(args.limit or 19, 19)
    topics = []
    for i in range(n):
        pageno = 6 + i
        lr_no = i + 1
        title = TITLES[i]
        png = render_page(pageno, tmp)
        text = ocr(png)
        parsed = parse_page(text)
        topic = {'id': f'LR{lr_no:02d}', 'title': title,
                 'scenario': parsed['scenario'], 'sentences': parsed['sentences']}
        topics.append(topic)
        print(f"[LR{lr_no:02d}] {title:38s} scenario={len(parsed['scenario'])}ch "
              f"sentences={len(parsed['sentences'])}")
        if len(parsed['sentences']) != 7:
            print(f"    !!! 句子数不是 7：{len(parsed['sentences'])}")

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'topics': topics}, f, ensure_ascii=False, indent=1)
    print(f"\nSaved {OUT}")


if __name__ == '__main__':
    main()
