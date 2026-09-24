"""Build quiz.html from template.html + question data JSON."""
import json
import argparse
from pathlib import Path

ROOT = Path(__file__).parent
TEMPLATE = ROOT / 'template.html'
DEFAULT_DATA = ROOT / 'mock_data.json'


def build(data_path, out_path):
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    with open(TEMPLATE, 'r', encoding='utf-8') as f:
        template = f.read()

    html = template.replace('__QUIZ_DATA__', json.dumps(data, ensure_ascii=False))

    out_path = Path(out_path)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    # quick stats
    total_sets = sum(len(b['sets']) for b in data.values())
    total_q = sum(len(s['questions']) for b in data.values() for s in b['sets'].values())
    print(f'Generated {out_path}')
    print(f'  batches: {len(data)}, sets: {total_sets}, questions: {total_q}')
    print(f'  size: {len(html):,} bytes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default=str(DEFAULT_DATA), help='question data JSON')
    parser.add_argument('--out', default=str(ROOT / 'quiz.html'), help='output HTML')
    args = parser.parse_args()
    build(args.data, args.out)
