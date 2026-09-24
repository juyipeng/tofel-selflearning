"""Extract original embedded images from the reading question docx files.

Each reading set (7.1A, 7.5C, ...) ships as a PDF/Word pair with IDENTICAL
content, plus one Answer_Key docx. The Word file's `word/media/*` hold the
ORIGINAL images (PNG/JPEG, lossless-or-better quality); the PDF re-compresses
them to JPEG (~2% ratio). So we extract from the .docx, not the PDF.

Output layout:

    reading/images/<set>/<module>_<nn>.<ext>     e.g. 7.1A/M1_01.png
    reading/images/manifest.json                 one record per image

The image order inside the document is the numeric order of `imageN.ext`
(verified against word/document.xml for every file).
"""
import json
import re
import zipfile
from io import BytesIO
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).parent
RAW = ROOT / 'raw-data' / 'extracted' / '7月阅读真题汇总'
OUT = ROOT / 'images'


def media_key(name: str) -> int:
    """Sort key: numeric suffix in imageN.ext -> N."""
    m = re.search(r'(\d+)\s*(?:\.|$)', Path(name).name)
    return int(m.group(1)) if m else 0


def module_of(docx_name: str) -> str:
    if docx_name.startswith('M1_'):
        return 'M1'
    if docx_name.startswith('M2H_'):
        return 'M2H'
    return 'UNKNOWN'


def extract_docx_images(docx_path: Path, set_name: str, module: str, out_dir: Path):
    """Extract word/media/* images (in document order) into out_dir."""
    records = []
    with zipfile.ZipFile(docx_path) as z:
        media = [
            n for n in z.namelist()
            if n.startswith('word/media/') and not n.endswith('/')
        ]
        media.sort(key=media_key)

        for i, name in enumerate(media, 1):
            data = z.read(name)
            ext = Path(name).suffix.lower().lstrip('.') or 'bin'
            out_name = f'{module}_{i:02d}.{ext}'
            out_path = out_dir / out_name
            out_path.write_bytes(data)

            # probe dimensions (best-effort; unknown formats just skip)
            w = h = fmt = None
            try:
                im = Image.open(BytesIO(data))
                w, h = im.size
                fmt = im.format
            except Exception:
                pass

            records.append({
                'set': set_name,
                'module': module,
                'index': i,
                'image_file': str(out_path.relative_to(ROOT)),
                'source_docx': str(docx_path.relative_to(ROOT)),
                'source_media': name,
                'format': fmt or ext,
                'width': w,
                'height': h,
            })
    return records


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    docx_files = sorted(RAW.rglob('*.docx'))
    reading_docx = [
        p for p in docx_files
        if not ('Answer' in p.name or 'Answer' in p.parent.name)
    ]

    manifest = []
    print(f'found {len(reading_docx)} reading docx files\n')
    for docx in reading_docx:
        set_name = docx.parent.name
        module = module_of(docx.name)
        out_dir = OUT / set_name
        out_dir.mkdir(parents=True, exist_ok=True)

        recs = extract_docx_images(docx, set_name, module, out_dir)
        manifest.extend(recs)
        print(f'{set_name:8s} {module:4s} {len(recs):3d} images  <- {docx.name}')

    manifest_path = OUT / 'manifest.json'
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    total = len(manifest)
    sets = sorted({r['set'] for r in manifest})
    print(f'\nDone: {total} images across {len(sets)} sets -> {OUT}')
    print(f'manifest -> {manifest_path}')


if __name__ == '__main__':
    main()
