#!/usr/bin/env python
"""合并 LR(OCR) + INT(ASR) -> speaking/app/manifest.json，并把音频拷到 app/audio/。

音频路径（相对 app/）：
  audio/listen_and_repeat/LR01/sentence_01.mp3
  audio/take_an_interview/INT01/question_01.mp3
"""
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
RAW_AUDIO = os.path.join(ROOT, 'raw-data', 'audio')
APP = os.path.join(ROOT, 'app')
APP_AUDIO = os.path.join(APP, 'audio')
OUT = os.path.join(APP, 'manifest.json')


def main():
    lr = json.load(open(os.path.join(DATA, 'lr.json'), encoding='utf-8'))
    intd = json.load(open(os.path.join(DATA, 'int.json'), encoding='utf-8'))

    lr_out = []
    for t in lr['topics']:
        sentences = []
        for i, s in enumerate(t['sentences'], 1):
            sentences.append({
                'no': i,
                'text': s,
                'audio': f'audio/listen_and_repeat/{t["id"]}/sentence_{i:02d}.mp3',
            })
        lr_out.append({'id': t['id'], 'title': t['title'],
                       'scenario': t['scenario'], 'sentences': sentences})

    int_out = []
    for u in intd['units']:
        questions = []
        for i, q in enumerate(u['questions'], 1):
            questions.append({
                'no': i,
                'text': q,
                'audio': f'audio/take_an_interview/{u["id"]}/question_{i:02d}.mp3',
            })
        int_out.append({'id': u['id'], 'title': u['title'], 'questions': questions})

    # 拷贝音频树
    if os.path.exists(APP_AUDIO):
        shutil.rmtree(APP_AUDIO)
    shutil.copytree(RAW_AUDIO, APP_AUDIO)

    manifest = {
        'title': '新托福口语 7 月回顾',
        'lr': lr_out,
        'int': int_out,
    }
    os.makedirs(APP, exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    n_lr = sum(len(t['sentences']) for t in lr_out)
    n_int = sum(len(u['questions']) for u in int_out)
    print(f'LR: {len(lr_out)} 主题 / {n_lr} 句')
    print(f'INT: {len(int_out)} 单元 / {n_int} 题')
    print(f'Saved {OUT}')
    n_audio = sum(len(files) for _, _, files in os.walk(APP_AUDIO))
    print(f'Audio files copied: {n_audio}')


if __name__ == '__main__':
    main()
