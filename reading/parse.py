"""Parse OCR text into structured question data, merged with the answer key.

Pipeline stage 2. Reads data/ocr.jsonl + data/answers.json, produces
data/questions.json with, per set, an ordered list of units:

    unit = {
      "type": "fill_in" | "passage",
      # fill_in:
      "paragraph": [...],   # list of tokens; blank positions are dicts
      "blanks": [{q, full, prefix, suffix, blank_len}, ...],
      # passage:
      "title": str,
      "questions": [{q, prompt, options, answer, kind}, ...],
    }

Key facts driving the logic:
- M1: 2 fill-in images (Q1-10, Q11-20) then 15 MCQ images (Q21-35).
- M2: 1 fill-in image (Q1-10) then 5 MCQ images (Q11-15), preceded by
  "Module 2" / "Reading" header images that carry no questions.
- MCQ question number = deterministic from image order (anchored at Q21/Q11).
"""
import json
import re
from pathlib import Path

from detect_squares import detect_squares

ROOT = Path(__file__).parent
DATA = ROOT / 'data'


# ---------------------------------------------------------------- loading

def load_ocr():
    recs = [json.loads(l) for l in open(DATA / 'ocr.jsonl', encoding='utf-8')]
    return recs


def load_answers():
    return json.loads((DATA / 'answers.json').read_text(encoding='utf-8'))


# ---------------------------------------------------------------- classification

def classify(raw):
    low = raw.lower()
    # intro/instruction pages (not questions)
    if 'reading section' in low or 'type of task' in low:
        return 'header'
    if 'fill in the missing letters' in low:
        return 'fill_in'
    if re.search(r'question \d+ of', low):
        return 'mcq'
    if re.search(r'\bread (a|an|the)?\b', low) and len(raw) > 80:
        return 'mcq'
    if 'module 2' in low and len(raw) < 300:
        return 'header'
    if 'end of reading' in low:
        return 'end'
    return 'mcq'  # scroll continuation


# ---------------------------------------------------------------- fill-in

def reconstruct_fill_in(raw, answers):
    """Reconstruct a fill-in paragraph: replace blanked words with a marker,
    and attach the ordered answers. answers = {q: {prefix, suffix, full, blank_len}}.

    Match rule: an OCR token t matches answer word w iff w.startswith(t) — i.e.
    the token is a (possibly OCR-mangled) truncation of the full word. This
    avoids matching a long word like 'these' against 'that'.
    """
    lines = [l.strip() for l in raw.split('\n') if l.strip()]
    body = ' '.join(lines[1:]) if lines and 'fill in' in lines[0].lower() else ' '.join(lines)
    body = re.sub(r'_+', ' ', body)  # neutralize stray underscores
    toks = body.split()

    qs = sorted(answers.keys(), key=int)
    blanks = []
    pos = 0
    for q in qs:
        a = answers[q]
        full = a['full'].lower()
        prefix = a['prefix'].lower()
        found = None
        for i in range(pos, len(toks)):
            t = toks[i].lower()
            # token is a truncation of the full word (or the full word itself)
            if full.startswith(t) and len(t) >= 1:
                found = i
                break
        if found is not None:
            blanks.append({'q': q, 'full': a['full'], 'prefix': a['prefix'],
                           'suffix': a['suffix'], 'blank_len': a['blank_len'],
                           'token_index': found})
            toks[found] = a['prefix']  # keep the visible prefix
            pos = found + 1
        else:
            # word dropped by OCR: insert it right after the last placed blank
            # so all blanks are present and in answer-key order (approx position).
            toks.insert(pos, a['prefix'])
            blanks.append({'q': q, 'full': a['full'], 'prefix': a['prefix'],
                           'suffix': a['suffix'], 'blank_len': a['blank_len'],
                           'token_index': pos, 'inserted': True})
            pos += 1
    return toks, blanks


# ---------------------------------------------------------------- mcq content

def strip_header(raw):
    """Remove the toeflibt / Volume Help / Question X / timer header."""
    lines = raw.split('\n')
    out = []
    for l in lines:
        s = l.strip()
        low = s.lower()
        if re.match(r'^(toefl|volume|help|review|back|next|reading|question \d+)', low):
            continue
        if re.search(r'\d{2}:\d{2}:\d{2}', low) or 'hide time' in low:
            continue
        out.append(l)
    return '\n'.join(out)


def split_mcq(raw):
    """Best-effort split of an MCQ image text into (article, question, options)."""
    text = strip_header(raw)
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # options are typically the last 4 short lines (or bullet lines)
    opts = []
    for i in range(len(lines) - 1, -1, -1):
        l = lines[i]
        if re.match(r'^([A-D][.)]|[•◦○●\-–]|■|�)', l) or (
                len(l.split()) <= 8 and len(opts) < 4):
            opts.insert(0, re.sub(r'^[A-D][.)]\s*', '', re.sub(r'^[•◦○●\-–]\s*', '', l)))
        else:
            break
    body_lines = lines[:len(lines) - len(opts)]

    # question = last sentence-ish line of body; article = the rest
    question = body_lines[-1] if body_lines else ''
    article = '\n'.join(body_lines[:-1]) if len(body_lines) > 1 else ''
    return article, question, opts


# ---------------------------------------------------------------- passage grouping

def passage_words(raw):
    """Header-stripped content words for grouping consecutive MCQ images."""
    text = strip_header(raw)
    # drop a leading instruction like 'Read a ...' (optional article/notice)
    text = re.sub(r'\bRead (?:a|an|the)\s*[a-z ]+?[.?!]\s*', '', text, flags=re.I)
    words = re.findall(r'[a-z]{2,}', text.lower())
    return set(words)


def passage_title(raw):
    """A human-readable title for the passage (first meaningful line)."""
    text = strip_header(raw)
    text = re.sub(r'\bRead (?:a|an|the)\s*[a-z ]+?[.?!]\s*', '', text, flags=re.I)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    return lines[0][:80] if lines else ''


# ---------------------------------------------------------------- main

def process_set(set_name, answers, ocr_by_mod):
    units = []
    m1 = answers.get('M1', {})
    m2 = answers.get('M2', {})

    for module, a in (('M1', m1), ('M2H', m2)):
        recs = sorted(ocr_by_mod.get((set_name, module), []), key=lambda r: r['index'])
        if not recs:
            continue
        fill_ans = a.get('fill_in', {})
        mcq_ans = a.get('mcq', {})

        # separate fill-in images (they come first)
        fill_recs = [r for r in recs if classify(r['raw']) == 'fill_in']
        mcq_recs = [r for r in recs if classify(r['raw']) != 'fill_in']

        # -- fill-in units: each fill-in image = one paragraph, blanks mapped
        #    to answer key in the order the paragraphs appear (Q1-10, Q11-20).
        fill_qs = sorted(fill_ans.keys(), key=int)
        per_para = len(fill_qs) // max(1, len(fill_recs))
        for i, r in enumerate(fill_recs):
            chunk = {q: fill_ans[q] for q in fill_qs[i * per_para:(i + 1) * per_para]}
            toks, blanks = reconstruct_fill_in(r['raw'], chunk)
            units.append({'type': 'fill_in', 'module': module, 'image': r['image_file'],
                          'paragraph': toks, 'blanks': blanks})

        # -- mcq: question numbers deterministic from order
        start_q = 21 if module == 'M1' else 11
        qnum = start_q
        passages = []  # list of {title, words, questions: []}
        prev_words = None
        for r in mcq_recs:
            raw = r['raw']
            if classify(raw) in ('header', 'end'):
                continue
            # explicit question number in header wins
            m = re.search(r'Question (\d+) of', raw)
            cur_q = int(m.group(1)) if m else qnum
            qnum = cur_q + 1

            words = passage_words(raw)
            # new passage if word overlap drops (or no prior passage)
            same = prev_words is not None and _overlap(prev_words, words) > 0.25
            if not same:
                passages.append({'title': passage_title(raw), 'words': words,
                                 'questions': []})
            prev_words = words

            article, question, opts = split_mcq(raw)
            qdict = {
                'q': cur_q,
                'prompt': question,
                'options': opts,
                'answer': mcq_ans.get(str(cur_q)),
                'kind': _mcq_kind(question),
                'image': r['image_file'],
                'article': article,
            }
            # sentence-insertion detection via ■ markers in the image
            img_path = ROOT / r['image_file']
            if img_path.exists():
                sq = detect_squares(img_path)
                body_sq = [s for s in sq if s[1] > 120]  # ignore header band
                article_sq = sorted([s for s in body_sq if s[0] < 900],
                                    key=lambda s: s[1])  # left column, top->bottom
                if len(article_sq) >= 3:
                    qdict['kind'] = 'insert'
                    # only the article ■ markers are the clickable insertion points
                    qdict['squares'] = [(s[0], s[1], s[2], s[3]) for s in article_sq]
                    ans = qdict['answer'] or ''
                    if ans.isdigit():
                        qdict['answer_pos'] = int(ans)
                    elif ans and ans[0] in 'ABCD':
                        qdict['answer_pos'] = ord(ans[0]) - ord('A') + 1
            passages[-1]['questions'].append(qdict)

        for p in passages:
            units.append({'type': 'passage', 'module': module, 'title': p['title'],
                          'questions': p['questions']})

    return units


def _overlap(a, b):
    wa, wb = (a if isinstance(a, set) else set(a.split()),
              b if isinstance(b, set) else set(b.split()))
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _mcq_kind(prompt):
    low = prompt.lower()
    if 'closest in meaning' in low or 'synonym' in low:
        return 'vocab'
    if 'infer' in low or 'imply' in low or 'suggest' in low:
        return 'inference'
    if 'except' in low or 'not' in low:
        return 'except'
    if 'main' in low or 'purpose' in low or 'topic' in low:
        return 'main'
    if 'four square' in low or 'where would' in low or 'best fit' in low:
        return 'insert'
    return 'detail'


def main():
    recs = load_ocr()
    answers = load_answers()

    from collections import defaultdict
    ocr_by_mod = defaultdict(list)
    for r in recs:
        ocr_by_mod[(r['set'], r['module'])].append(r)

    result = {}
    for set_name in sorted(answers.keys()):
        try:
            units = process_set(set_name, answers[set_name], ocr_by_mod)
            result[set_name] = units
            n_fill = sum(1 for u in units if u['type'] == 'fill_in')
            n_pass = sum(1 for u in units if u['type'] == 'passage')
            n_q = sum(len(u['questions']) for u in units if u['type'] == 'passage')
            print(f'{set_name:8s} fill_units={n_fill} passages={n_pass} mcq_q={n_q}')
        except Exception as e:
            print(f'{set_name:8s} ERROR: {type(e).__name__}: {e}')

    out = DATA / 'questions.json'
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\nSaved -> {out}')


if __name__ == '__main__':
    main()
