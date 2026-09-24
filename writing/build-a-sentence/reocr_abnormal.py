"""Re-OCR the abnormal GLM records (missing sentence/options) with a more
explicit 3-part prompt. Updates glm_26.X.jsonl in place for records that get a
valid parse.

Abnormal = options empty, options contain '____', sentence empty, or sentence
contains '____'.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / 'data'

sys.path.insert(0, str(ROOT.parent))   # 仓库根目录
from shared.ocr import ocr_image as _ocr_image

PROMPT = (
    'This is a TOEFL "make a sentence" question. It has THREE parts stacked vertically:\n'
    '1. top: a prompt sentence (context)\n'
    '2. middle: a target sentence with blank underline slots where words were removed\n'
    '3. bottom: candidate words\n'
    'Transcribe all three parts. Use ___ for each blank underline in the middle '
    'sentence. Put the bottom candidate words on the last line, separated by spaces.'
)

GLM_FILES = [
    ('BS_1月', 'glm_26.1.jsonl'),
    ('BS_2月', 'glm_26.2.jsonl'),
    ('BS_3月', 'glm_26.3.jsonl'),
    ('BS_4月', 'glm_26.4.jsonl'),
    ('BS_5月', 'glm_26.5.jsonl'),
]


def ocr_image(img_path, retries=4):
    """重跑异常图：用更明确的「三部分」提示词，多给一次重试。"""
    return _ocr_image(img_path, prompt=PROMPT, retries=retries)


def parse(text):
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


def is_abnormal(rec):
    sent = rec.get('sentence', [])
    opts = rec.get('options', [])
    if not opts or not sent:
        return True
    if any(re.search(r'_+', str(w)) for w in opts):
        return True
    if any(w is not None and re.search(r'_+', str(w)) for w in sent):
        return True
    if sum(1 for x in sent if x is None) == 0:
        return True  # sentence has no blanks -> GLM-OCR missed the blank markers
    return False


def main():
    total_fixed = 0
    total_abnormal = 0
    for batch, fname in GLM_FILES:
        path = DATA / fname
        if not path.exists():
            continue
        with open(path, 'r', encoding='utf-8') as f:
            records = [json.loads(line) for line in f if line.strip()]

        fixed = 0
        abnormal = 0
        for i, rec in enumerate(records):
            if not is_abnormal(rec):
                continue
            abnormal += 1
            img = ROOT / rec['image_file']
            if not img.exists():
                continue
            text = ocr_image(img)
            if text is None:
                continue
            prompt, sentence, options = parse(text)
            if prompt is None or not sentence or not options:
                continue
            if any(re.search(r'_+', str(w)) for w in options):
                continue
            records[i] = {
                'image_file': rec['image_file'],
                'set_num': rec['set_num'],
                'page_in_set': rec['page_in_set'],
                'image_index': rec['image_index'],
                'prompt': prompt,
                'sentence': sentence,
                'options': options,
                'raw': text,
            }
            fixed += 1

        with open(path, 'w', encoding='utf-8') as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')
        print(f'{batch}: {abnormal} abnormal, {fixed} fixed')
        total_fixed += fixed
        total_abnormal += abnormal

    print(f'TOTAL: {total_abnormal} abnormal, {total_fixed} fixed')


if __name__ == '__main__':
    main()
