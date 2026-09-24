"""Re-derive 待填句/待选词 split using OCR 'top' coordinate (bottom = options)."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent


def normalize(s):
    s = s.lower().strip()
    s = re.sub(r'[^a-z0-9 ]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def load_raw():
    raw = {}
    for batch, fname in [('BS_4月', 'data/26.4.jsonl'), ('BS_5月', 'data/26.5.jsonl')]:
        with open(ROOT / fname, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                key = (batch, rec['set_num'], rec['page_in_set'], rec['image_index'])
                raw[key] = [(w['word'], w['rect']['top']) for w in rec['words'][1:]]
    return raw


def detect_option_indices(tops):
    """Return set of indices (into tops) that are options (bottom cluster)."""
    n = len(tops)
    if n == 0:
        return set()
    if n == 1:
        return {0}  # only one word -> it's the option (sentence empty)
    order = sorted(range(n), key=lambda i: tops[i])
    best_i, best_gap = 1, -1
    for i in range(1, n):
        gap = tops[order[i]] - tops[order[i-1]]
        if gap > best_gap:
            best_gap = gap
            best_i = i
    # words below the largest gap are options
    return set(order[best_i:])


def main():
    raw = load_raw()

    with open(ROOT / 'data/questions_input.json', 'r', encoding='utf-8') as f:
        q_input = json.load(f)

    with open(ROOT / 'data/questions_final.json', 'r', encoding='utf-8') as f:
        final = json.load(f)

    flat = []
    for b in ['BS_4月', 'BS_5月']:
        for set_key in sorted(final[b]['sets'].keys()):
            for q in final[b]['sets'][set_key]['questions']:
                flat.append(q)
    assert len(flat) == len(q_input), f'{len(flat)} != {len(q_input)}'

    new_data = {'BS_4月': {'name': 'BS 4月真题', 'sets': {}}, 'BS_5月': {'name': 'BS 5月真题', 'sets': {}}}
    missing = 0

    for qi, (inp, qf) in enumerate(zip(q_input, flat)):
        key = (inp['batch'], inp['set_num'], inp['page_in_set'], inp['image_index'])
        raw_words = raw.get(key, [])
        if not raw_words:
            missing += 1
            continue
        tops = [t for _, t in raw_words]
        opt_idx = detect_option_indices(tops)
        # label each raw word: is_option
        raw_info = []
        for i, (w, t) in enumerate(raw_words):
            raw_info.append((w, t, i in opt_idx))
        # exact normalized map (word -> is_option)
        norm_map = {}
        for w, t, is_opt in raw_info:
            norm_map[normalize(w)] = is_opt

        s = qf['sentence']
        a = qf['answers']
        ai = 0
        full = []
        for x in s:
            if x is None:
                full.append(a[ai]); ai += 1
            else:
                full.append(x)

        # rebuild: split merged agent elements into raw components, re-label each
        new_sentence, new_answers = [], []
        for el in full:
            n_el = normalize(el)
            if n_el in norm_map:
                is_opt = norm_map[n_el]
                if is_opt:
                    new_answers.append(el); new_sentence.append(None)
                else:
                    new_sentence.append(el)
            else:
                # merge: find raw components (substrings) and order by position
                comps = []
                for w, t, is_opt in raw_info:
                    nw = normalize(w)
                    if nw and nw in n_el:
                        comps.append((n_el.find(nw), w, is_opt))
                comps.sort(key=lambda c: c[0])
                if not comps:
                    new_sentence.append(el)
                    continue
                for _, w, is_opt in comps:
                    if is_opt:
                        new_answers.append(w); new_sentence.append(None)
                    else:
                        new_sentence.append(w)

        # options in OCR original (scrambled) order
        scrambled_options = [w for i, (w, t) in enumerate(raw_words) if i in opt_idx]

        q = {'prompt': qf.get('prompt', inp['strs'][0]),
             'sentence': new_sentence, 'options': scrambled_options, 'answers': new_answers}
        b = inp['batch']
        sk = f"set_{inp['set_num']:02d}"
        if sk not in new_data[b]['sets']:
            new_data[b]['sets'][sk] = {'name': f"第 {inp['set_num']} 套", 'questions': []}
        new_data[b]['sets'][sk]['questions'].append(q)

    with open(ROOT / 'data/questions_final.json', 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

    nq = sum(len(s['questions']) for b in new_data for s in new_data[b]['sets'].values())
    print(f'Recomputed: {nq} questions, {missing} missing raw coords')


if __name__ == '__main__':
    main()
