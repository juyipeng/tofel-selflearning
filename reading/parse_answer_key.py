"""Parse all Answer_Key.docx files into structured answers JSON.

Each Answer_Key.docx is a Word doc with section-label paragraphs interleaved
with answer tables. The Reading tables look like:

    [para] Noble_20260 701A _Reading_M1
    [table] 4 cols: (Q, fill-in answer) x2 side by side -> Q1-20 fill-in, Q21-35 MCQ
    [para] Noble_20260 701A _Reading_M2+
    [table] 2 cols: (Q, answer) -> Q1-10 fill-in, Q11-15 MCQ
    [para] ... _Listening_M1 ...   (ignored)

Fill-in answer cells hold the word split at the blank: "know ledge" = the word
"knowledge" with suffix "ledge" blanked. MCQ answer cells are a single letter
(A-D) or a single digit (sentence-insertion position).

Output: data/answers.json  { set: { test_id, form, M1/M2: { fill_in: {q: {prefix, suffix, full, blank_len}}, mcq: {q: answer} } } }
"""
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).parent
RAW = ROOT / 'raw-data' / 'extracted' / '7月阅读真题汇总'
OUT = ROOT / 'data'

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
WNS = {'w': W}


def cell_text(tc):
    return ' '.join(t.text or '' for t in tc.iter(f'{{{W}}}t')).strip()


def row_cells(tr):
    return [cell_text(tc) for tc in tr.findall('w:tc', WNS)]


def iter_body(doc_xml):
    """Yield ('p', text) and ('tbl', [[cells]]) in document order."""
    root = ET.fromstring(doc_xml)
    body = root.find(f'{{{W}}}body')
    for el in body:
        tag = el.tag.split('}')[1]
        if tag == 'p':
            txt = ' '.join(t.text or '' for t in el.iter(f'{{{W}}}t')).strip()
            yield ('p', txt)
        elif tag == 'tbl':
            rows = [row_cells(tr) for tr in el.findall('w:tr', WNS)]
            yield ('tbl', rows)


def parse_section_label(txt):
    m = re.search(r'_?(Reading_M[12]|Listening|Writing|Speaking)', txt)
    return m.group(1) if m else None


def parse_answer_table(rows):
    """Flatten a (Q, answer) table into {q: answer_str}. Answer_str for
    fill-in keeps the internal space (prefix suffix); for MCQ it's one token."""
    answers = {}
    for cells in rows:
        # pairs of (q, answer); some rows have 2 pairs (4 cols) or 1 pair (2 cols)
        pairs = [cells[i:i + 2] for i in range(0, len(cells), 2)]
        for q, ans in pairs:
            q = q.strip()
            ans = ans.strip()
            if not q or not ans:
                continue
            # normalize question number (strip trailing punctuation)
            qnum = q
            if ans:  # keep answer as-is; empty cells skipped above
                answers[qnum] = ans
    return answers


def classify_answer(ans):
    """Classify one answer cell:
    - 1 token  -> MCQ (letter A-D, or digit = sentence-insertion position)
    - multi-token forming a single short word -> fill-in (split at first token
      = visible prefix; the rest, with internal spaces, is the blanked suffix)
    - multi-token long phrase -> sentence-insertion (key records the sentence)
    """
    ans = ans.strip()
    toks = ans.split()
    if len(toks) == 1:
        return ('mcq', ans)
    joined = ''.join(toks)
    if len(joined) <= 20:
        prefix = toks[0]
        suffix = ''.join(toks[1:])
        return ('fill_in', {
            'prefix': prefix,
            'suffix': suffix,
            'full': prefix + suffix,
            'blank_len': len(suffix),
        })
    return ('insert_sentence', ans)


def parse_one(docx_path):
    z = zipfile.ZipFile(docx_path)
    doc = z.read('word/document.xml')

    current_section = None
    header = None
    result = {'M1': {'fill_in': {}, 'mcq': {}, 'insert': {}},
              'M2': {'fill_in': {}, 'mcq': {}, 'insert': {}}}

    for kind, payload in iter_body(doc):
        if kind == 'p':
            if not payload:
                continue
            sec = parse_section_label(payload)
            if sec:
                current_section = sec
                # capture test_id + form from the header line
                m = re.match(r'([\w-]+)\s+(\S+)\s*_', payload)
                if m and header is None:
                    header = {'test_id': m.group(1), 'form': m.group(2)}
            continue
        # table
        if current_section in ('Reading_M1', 'Reading_M2'):
            module = 'M1' if current_section == 'Reading_M1' else 'M2'
            answers = parse_answer_table(payload)
            for q, ans in answers.items():
                kind2, val = classify_answer(ans)
                target = result[module][kind2] if kind2 in result[module] else result[module]['insert']
                target[q] = val

    return {'test_id': header['test_id'] if header else None,
            'form': header['form'] if header else None,
            'M1': result['M1'], 'M2': result['M2']}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    all_answers = {}
    for docx in sorted(RAW.rglob('*Answer*.docx')):
        set_name = docx.parent.name
        try:
            parsed = parse_one(docx)
            all_answers[set_name] = parsed
            parts = []
            for mod in ('M1', 'M2'):
                f, m, ins = len(parsed[mod]['fill_in']), len(parsed[mod]['mcq']), len(parsed[mod]['insert'])
                parts.append(f'{mod}: fill={f} mcq={m} insert={ins}')
            # flag digit (position) answers within mcq
            digit_ans = {}
            for mod in ('M1', 'M2'):
                for q, a in parsed[mod]['mcq'].items():
                    if a.isdigit():
                        digit_ans[f'{mod} Q{q}'] = a
            print(f'{set_name:8s} ' + '  '.join(parts))
            if digit_ans or any(parsed[m]['insert'] for m in ('M1', 'M2')):
                print(f'           digit-answers={digit_ans}  insert-sentences=' +
                      {m: parsed[m]['insert'] for m in ('M1', 'M2')}.__repr__()[:120])
        except Exception as e:
            print(f'{set_name:8s} ERROR: {e}')

    out_path = OUT / 'answers.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(all_answers, f, ensure_ascii=False, indent=2)
    print(f'\nSaved {len(all_answers)} sets -> {out_path}')


if __name__ == '__main__':
    main()
