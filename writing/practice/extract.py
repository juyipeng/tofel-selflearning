"""拆题脚本：从「写作精选套题练习10套.zip」提取 Write an Email 和 Academic Discussion 题目。

流程：
  1. 解压 zip（zip 内中文文件名是 UTF-8 字节被 Python 按 cp437 误读，需 encode('cp437').decode('utf-8') 还原）
  2. 对每个 PDF：pdfinfo 取页数 → pdftoppm 渲染最后几页为 PNG
  3. GLM-OCR（本地 Ollama glm-ocr:q8_0）逐页识别
  4. 按内容定位 Email 页（含 "Write an email to"）和 Discussion 页（含 "Your professor is teaching"）
  5. 解析成结构化 JSON，写到 data/questions.json（resume-safe，已处理的套题跳过）

复用 make-a-sentence 项目的 OCR 经验：简单提示词、超宽图先缩小。
"""
import json
import re
import sys
import subprocess
import tempfile
import zipfile
import argparse
import os
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).parent
DATA = ROOT / 'data'
RAW = DATA / 'raw'

sys.path.insert(0, str(ROOT.parent.parent))   # 仓库根目录
from shared.ocr import ocr_b64, to_b64

# 每个 PDF 只渲染最后 N 页（Email 倒数第 2 页、Discussion 最后一页）
TAIL_PAGES = 4

ZIP_PATH = Path(r'e:/code/personal_projects/TOEFL-learning/writing/写作精选套题练习10套.zip')
OUT_JSON = DATA / 'questions.json'


def decode_name(name: str) -> str:
    """zip 内文件名：UTF-8 字节被 zipfile 按 cp437 解码，这里还原。"""
    try:
        return name.encode('cp437').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        return name


def _ocr_b64(b64: str, retries: int) -> str:
    """本模块各调用方按「空串即失败」处理，故这里把 None 收敛成 ''。"""
    return ocr_b64(b64, retries=retries) or ''


def ocr_image(img_path: Path, retries: int = 2) -> str:
    im = Image.open(img_path).convert('RGB')
    w, h = im.size
    if w > 1600:
        im = im.resize((1600, max(1, int(h * 1600 / w))))
    w, h = im.size
    # 竖版/超高页：GLM-OCR 会漏掉底部内容（学生发言在下半页），切成上下两块分别识别，
    # 带 50px 重叠防漏行，拼接时去掉边界重复行。
    if h > 1300:
        mid = h // 2
        top = im.crop((0, 0, w, mid + 50))
        bot = im.crop((0, max(0, mid - 50), w, h))
        a = _ocr_b64(to_b64(top), retries)
        b = _ocr_b64(to_b64(bot), retries)
        out, prev = [], ''
        for l in (a + '\n' + b).split('\n'):
            s = l.strip()
            if s and s == prev:
                continue
            prev = s
            out.append(l)
        return '\n'.join(out)
    return _ocr_b64(to_b64(im), retries)


def render_tail_pages(pdf_path: Path, out_dir: Path, n_pages: int) -> list:
    """渲染最后 n_pages 页为 PNG，返回 [(页码, png路径)]。"""
    info = subprocess.run(['pdfinfo', str(pdf_path)], capture_output=True, text=True, errors='replace')
    total = 1
    for line in info.stdout.splitlines():
        if 'Pages' in line:
            total = int(line.split(':')[-1].strip())
            break
    start = max(1, total - n_pages + 1)
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(['pdftoppm', '-png', '-r', '150',
                    '-f', str(start), '-l', str(total),
                    str(pdf_path), str(out_dir / 'page')],
                   check=True, capture_output=True)
    pages = sorted(out_dir.glob('page-*.png'))
    # page-14.png -> 14
    result = []
    for p in pages:
        try:
            pageno = int(p.stem.split('-')[-1])
        except ValueError:
            continue
        result.append((pageno, p))
    return result


def blocks(text: str) -> list:
    """按空行切成块，去掉每块内部多余空白。"""
    parts = re.split(r'\n\s*\n', text.strip())
    out = []
    for p in parts:
        p = '\n'.join(line.strip() for line in p.split('\n') if line.strip())
        if p:
            out.append(p)
    return out


def parse_email(text: str) -> dict:
    # 任务行：Write an email to ...
    task = ''
    recipient = ''
    mt = re.search(r'Write an email to[^\n]*', text, re.I)
    if mt:
        task = mt.group(0).strip()
        rest = task.split('Write an email to', 1)[1].strip()
        rest = re.sub(r'[.,]\s*In your email.*$', '', rest, flags=re.I)
        rest = rest.rstrip('.').strip()
        # 带称呼（Mr./Ms./Dr./Professor …）或裸名（如 Jasmine）
        tm = re.search(r'(Mr\.?|Ms\.?|Mrs\.?|Dr\.?|Professor|Prof\.?)\s+[A-Z][a-zA-Z]*', rest)
        if tm:
            recipient = tm.group(0)
        else:
            nm = re.search(r'[A-Z][a-zA-Z]+', rest)
            recipient = nm.group(0) if nm else rest

    # 情景：任务行之前的部分
    context = text[:mt.start()].strip() if mt else text.strip()
    context = re.sub(r'\n\s*In your email, do the following:?\s*$', '', context, flags=re.I).strip()
    # 7月真题里 Email 与组句题同页，任务行前面会残留组句题文字，识别到就清空
    if re.search(r'appropriate sentence', context, re.I):
        context = ''

    bullets = [b.strip() for b in re.findall(r'^\s*[-•]\s*(.+)$', text, re.M)]

    closing = ''
    mc = re.search(r'Write as much as you can[^\n]*', text, re.I)
    if mc:
        closing = mc.group(0).strip()

    return {
        'context': context,
        'task': task,
        'recipient': recipient,
        'bullets': bullets,
        'closing': closing,
    }


def _is_student_name(b: str) -> bool:
    b = b.strip()
    if len(b) > 30 or len(b.split()) > 2:
        return False
    if re.search(r'[.!?,]$', b):
        return False
    return bool(re.match(r'^[A-Z]', b))


# OCR 没识别出学生名字时，按顺序补一个通用名（内容为主，别显示 Student 1/2）
DEFAULT_STUDENT_NAMES = ['Kelly', 'Paul', 'Alex', 'Beth', 'Claire', 'Andrew', 'Daniel', 'Maria', 'Sara', 'Tom']


def parse_discussion(text: str) -> dict:
    # 引导句：到 "In your response" 之前（三选一题型可能没有这句）
    instruction = ''
    idx = text.lower().find('in your response')
    if idx > 0:
        instruction = text[:idx].strip()

    word_min = None
    mw = re.search(r'at least (\d+) words', text, re.I)
    if mw:
        word_min = int(mw.group(1))

    # 要求 bullet 只取 "In your response" 到 "An effective response"（教授正文里的 bullet 不算）
    req_section = ''
    mr = re.search(r'In your response.*?(?=An effective response|at least|Dr\.?|Professor|Prof\.?)', text, re.S | re.I)
    if mr:
        req_section = mr.group(0)
    requirements = [r.strip() for r in re.findall(r'^\s*[-•]\s*(.+)$', req_section, re.M)]

    # 去掉工具栏，并过滤「导语」块，剩下的才是教授提问 + 学生发言
    blks = [b for b in blocks(text) if not re.search(r'Cut\s+Paste\s+Undo\s+Redo', b, re.I)]
    preamble_kw = re.compile(
        r'In your response|Express and support|Make a contribution|at least \d+ words|Your professor is teaching', re.I)
    content = [b for b in blks if not preamble_kw.search(b)]

    prof_name = ''
    prof_text = ''
    students_raw = []

    name_idx = None
    for i, b in enumerate(content):
        if re.match(r'^(Dr\.?|Professor|Prof\.?)\s+[A-Z]', b):
            prof_name = b.strip()
            name_idx = i
            break

    if name_idx is not None:
        rest = content[name_idx + 1:]
        # 教授正文 = 名字后第一块，并吞掉随后的 bullet 列表 / 含问号的追问（三选一题型）
        prof_parts = [rest[0]] if rest else []
        j = 1
        while j < len(rest):
            b = rest[j]
            if b.strip().startswith('-') or '?' in b:
                prof_parts.append(b)
                j += 1
            else:
                break
        prof_text = '\n'.join(prof_parts)
        students_raw = rest[j:]
    else:
        # 教授名缺失（个别竖版页 OCR 漏了名字）：含 discuss/explor 教学引导语的句子是教授提问，
        # 其余是学生发言；OCR 丢空行导致学生发言与教授提问粘连时，按引导语位置切开
        prof_text = ''
        students_raw = []
        prof_done = False
        for b in content:
            m = re.search(r'\b(?:discuss\w*|explor\w*)', b, re.I)
            if m and not prof_done:
                start = max(b.rfind('. ', 0, m.start()) + 2,
                            b.rfind('? ', 0, m.start()) + 2,
                            b.rfind('\n', 0, m.start()) + 1)
                before = b[:start].strip()
                if before:
                    students_raw.append(before)
                prof_text = b[start:].strip()
                prof_done = True
            else:
                students_raw.append(b)
        if not prof_done:
            # 退化：含问号的块是教授提问
            q_idx = None
            for i, b in enumerate(content):
                if '?' in b:
                    q_idx = i
                    break
            if q_idx is not None:
                prof_text = content[q_idx]
                students_raw = [x for j, x in enumerate(content) if j != q_idx]
            else:
                students_raw = list(content)

    # 学生：名字单独成块时与下一块合并
    students = []
    i = 0
    while i < len(students_raw):
        b = students_raw[i]
        if _is_student_name(b) and i + 1 < len(students_raw):
            students.append({'name': b.strip(), 'text': students_raw[i + 1].strip()})
            i += 2
        else:
            students.append({'name': '', 'text': b.strip()})
            i += 1

    # 给缺名的学生补一个默认名（内容为主，名字随便起，别显示 Student 1/2）
    used = {s['name'] for s in students if s.get('name')}
    pool = [n for n in DEFAULT_STUDENT_NAMES if n not in used]
    k = 0
    for s in students:
        if not s.get('name'):
            s['name'] = pool[k % len(pool)] if pool else 'Classmate'
            k += 1

    return {
        'instruction': instruction,
        'requirements': requirements,
        'word_min': word_min,
        'professor': {'name': prof_name, 'text': prof_text},
        'students': students,
    }


def process_pdf(pdf_bytes: bytes, set_id: str, source: str) -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        pdf_path = tmp / 'q.pdf'
        pdf_path.write_bytes(pdf_bytes)

        pages = render_tail_pages(pdf_path, tmp / 'pages', TAIL_PAGES)

        email_raw = discussion_raw = None
        for pageno, png in pages:
            txt = ocr_image(png)
            if not txt:
                continue
            if email_raw is None and re.search(r'Write an email to', txt, re.I):
                email_raw = txt
            if discussion_raw is None and re.search(r'Your professor is teaching|In your response, you should do the following', txt, re.I):
                discussion_raw = txt

        # 保存原始 OCR 供校对
        (RAW / f'{set_id}.txt').write_text(
            f"=== EMAIL ===\n{email_raw or '(未识别)'}\n\n=== DISCUSSION ===\n{discussion_raw or '(未识别)'}\n",
            encoding='utf-8')

    email = parse_email(email_raw) if email_raw else None
    discussion = parse_discussion(discussion_raw) if discussion_raw else None

    return {
        'id': set_id,
        'source': source,
        'email': email,
        'discussion': discussion,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--zip', default=str(ZIP_PATH))
    parser.add_argument('--out', default=str(OUT_JSON))
    parser.add_argument('--limit', type=int, default=0, help='只处理前 N 套（0=全部）')
    args = parser.parse_args()

    DATA.mkdir(parents=True, exist_ok=True)

    # 读取已有结果（resume-safe + 多 zip 合并：保留其它 zip 已拆的套题）
    results = []
    if os.path.exists(args.out):
        with open(args.out, encoding='utf-8') as f:
            old = json.load(f)
        results = list(old.get('sets', []))

    def have_full(s):
        return bool(s.get('email')) and bool(s.get('discussion'))

    done = {s['id']: i for i, s in enumerate(results) if have_full(s)}

    source = os.path.basename(args.zip).replace('.zip', '')

    with zipfile.ZipFile(args.zip) as z:
        pdfs = [n for n in z.namelist()
                if n.endswith('.pdf') and '__MACOSX' not in n and '.DS_Store' not in n]
        pdfs.sort()

    if args.limit:
        pdfs = pdfs[:args.limit]

    def flush():
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump({'sets': results}, f, ensure_ascii=False, indent=2)

    for n in pdfs:
        name = decode_name(n)
        # set_id 形如 20260524B / 20260809B：取文件名开头 9 位
        base = os.path.basename(name)
        m = re.match(r'(\d{8}[A-Z])', base)
        set_id = m.group(1) if m else base[:10]

        if set_id in done:
            print(f'[skip] {set_id} (已存在)')
            continue

        print(f'[extract] {set_id} <- {base}')
        with zipfile.ZipFile(args.zip) as z:
            data = z.read(n)
        try:
            rec = process_pdf(data, set_id, source)
        except Exception as e:
            print(f'  FAILED {set_id}: {e}')
            rec = {'id': set_id, 'source': source, 'email': None, 'discussion': None}

        if set_id in done:
            results[done[set_id]] = rec
        else:
            results.append(rec)
            if have_full(rec):
                done[set_id] = len(results) - 1
        flush()

    print(f'\n完成：{len(results)} 套 -> {args.out}')


if __name__ == '__main__':
    main()
