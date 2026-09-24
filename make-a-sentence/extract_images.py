"""Extract embedded images from raw-data PDFs into images/ organized by set and page."""
import subprocess
import json
import math
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent
RAW = ROOT / 'raw-data'
OUT = ROOT / 'images'

PDFS = {
    'BS_1月': RAW / 'BS_1月真题（共7套）.pdf',
    'BS_2月': RAW / 'BS_2月真题（共19套）.pdf',
    'BS_3月': RAW / 'BS_3月真题（共35套）.pdf',
    'BS_4月': RAW / 'BS_4月真题（共26套）pdf.pdf',
    'BS_5月': RAW / 'BS_5月真题(共23套）.pdf',
}

PAGES_PER_SET = 2  # each set = 2 pages


def extract_one(name, pdf_path):
    set_dir_root = OUT / name
    set_dir_root.mkdir(parents=True, exist_ok=True)

    manifest = []  # list of {image_file, source_page, set_num, page_in_set, image_index}

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        prefix = tmp / 'img'
        # Extract all images with page number prefix: img-PPP-NNN.jpg
        subprocess.run(
            ['pdfimages', '-p', '-j', str(pdf_path), str(prefix)],
            check=True, capture_output=True,
        )

        # Group extracted files by page
        files = sorted(tmp.glob('img-*.jpg'))
        page_counter = {}  # page_num -> per-page image index
        for f in files:
            # filename like img-001-000.jpg
            stem = f.stem  # img-001-000
            parts = stem.split('-')
            page_num = int(parts[1])
            global_idx = int(parts[2])

            # per-page index
            per_page_idx = page_counter.get(page_num, 0)
            page_counter[page_num] = per_page_idx + 1

            set_num = math.ceil(page_num / PAGES_PER_SET)
            page_in_set = ((page_num - 1) % PAGES_PER_SET) + 1

            set_dir = set_dir_root / f'set_{set_num:02d}'
            set_dir.mkdir(parents=True, exist_ok=True)

            new_name = f'p{page_in_set:02d}_img_{per_page_idx:02d}.jpg'
            dest = set_dir / new_name
            shutil.move(str(f), str(dest))

            manifest.append({
                'image_file': str(dest.relative_to(ROOT)),
                'source_page': page_num,
                'set_num': set_num,
                'page_in_set': page_in_set,
                'image_index': per_page_idx,
                'global_image_index': global_idx,
            })

    # Write manifest
    manifest_path = OUT / f'{name}_manifest.json'
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f'{name}: {len(manifest)} images -> {set_dir_root}')


def main():
    OUT.mkdir(exist_ok=True)
    for name, pdf_path in PDFS.items():
        if not pdf_path.exists():
            print(f'SKIP {name}: PDF not found at {pdf_path}')
            continue
        extract_one(name, pdf_path)
    print('Done.')


if __name__ == '__main__':
    main()
