"""Build flashcards.html from vocab_data.json + template.html."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent

def main():
    # Load data
    with open(ROOT / 'vocab_data.json', 'r', encoding='utf-8') as f:
        vocab = json.load(f)

    # Load template
    with open(ROOT / 'template.html', 'r', encoding='utf-8') as f:
        template = f.read()

    # Build clean vocab array for embedding
    entries = []
    for v in vocab:
        entries.append({
            'word':        v.get('word', ''),
            'phonetic':    v.get('phonetic', ''),
            'pos':         v.get('pos', ''),
            'definition':  v.get('definition', ''),
            'phrase':      v.get('phrase', ''),
            'sentence':    v.get('sentence', ''),
            'phrase_cn':   v.get('phrase_cn', ''),
            'sentence_cn': v.get('sentence_cn', ''),
            'list':        v.get('list', 1),
        })

    vocab_json = json.dumps(entries, ensure_ascii=False)
    html = template.replace('__VOCAB_DATA__', vocab_json)

    out_path = ROOT / 'flashcards.html'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f'Generated {out_path}')
    print(f'  Words: {len(entries)}')
    print(f'  Size:  {len(html):,} bytes')

    # Stats
    missing_sentence = sum(1 for e in entries if not e['sentence'])
    missing_phrase_cn = sum(1 for e in entries if not e['phrase_cn'])
    missing_sentence_cn = sum(1 for e in entries if not e['sentence_cn'])
    if missing_sentence:
        print(f'  WARNING: {missing_sentence} entries missing sentence')
    if missing_phrase_cn:
        print(f'  WARNING: {missing_phrase_cn} entries missing phrase_cn')
    if missing_sentence_cn:
        print(f'  WARNING: {missing_sentence_cn} entries missing sentence_cn')

if __name__ == '__main__':
    main()
