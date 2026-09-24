"""Build questions_final.json from GLM-OCR layout data + agent answers.

Data flow:
  glm_26.X.jsonl  ->  build_agent_input.py  ->  agent batches  ->  agent answers
  glm_26.X.jsonl  +  agent answers  ->  merge_final.py  ->  questions_final.json

The split (sentence fixed parts vs options) comes from the image LAYOUT (already in
glm jsonl). The agent only supplies the correct ORDER of the options (grouped into
phrases). Everything else here is deterministic.
"""
import json
import re
import random
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / 'data'

GLM_FILES = [
    ('BS_1月', 'glm_26.1.jsonl'),
    ('BS_2月', 'glm_26.2.jsonl'),
    ('BS_3月', 'glm_26.3.jsonl'),
    ('BS_4月', 'glm_26.4.jsonl'),
    ('BS_5月', 'glm_26.5.jsonl'),
]


def strip_punct(s):
    """Strip sentence-final punctuation from a word/phrase."""
    return re.sub(r'[.!?,;:]+$', '', s).strip()


def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def regroup_answers(ans_list, cards):
    """Re-group LLM answers (semantic grouping) into spacing-based cards.

    cards: list of card word-lists in display order, e.g.
      [["do"], ["have","been","updated"], ["the","due","dates"], ["if"], ["you"]]
    Returns answers re-grouped so consecutive words of the same card stay together.
    """
    if not cards:
        return ans_list
    norm_to_card = {}
    for ci, card in enumerate(cards):
        for w in card:
            norm_to_card[norm(w)] = ci
    flat = [w for phrase in ans_list for w in phrase.split()]
    groups = []
    cur = []
    prev = -1
    for w in flat:
        cid = norm_to_card.get(norm(w), -2)
        if cur and cid != prev:
            groups.append(' '.join(cur))
            cur = []
        cur.append(w)
        prev = cid
    if cur:
        groups.append(' '.join(cur))
    return groups


def load_cards():
    """image_file -> cards (list of card word-lists), from rapidocr_group.py."""
    cards = {}
    path = DATA / 'rapidocr_cards.jsonl'
    if not path.exists():
        return cards
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            cards[rec['image_file']] = rec['cards']
    return cards


def load_glm():
    entries = []
    for batch, fname in GLM_FILES:
        path = DATA / fname
        if not path.exists():
            continue
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if batch == 'BS_1月' and rec['set_num'] == 7:
                    continue  # duplicate of set 6
                entries.append((batch, rec))
    return entries


def load_answers():
    """Combine all batch result files (batch_*_result.json) into one flat list."""
    batch_dir = DATA / 'agent_batches'
    ans = []
    for fn in sorted(batch_dir.glob('batch_*_result.json')):
        ans.extend(json.load(open(fn, 'r', encoding='utf-8')))
    return ans


def main():
    glm = load_glm()
    answers = load_answers()
    assert len(glm) == len(answers), f'{len(glm)} glm != {len(answers)} answers'

    rng = random.Random(42)
    new_data = {}
    skipped = 0
    cards = load_cards()

    for (batch, rec), ans in zip(glm, answers):
        # agent answers (grouped phrases, correct order)
        if isinstance(ans, dict):
            ans_list = ans['answers']
        else:
            ans_list = ans
        ans_list = [strip_punct(w) for w in ans_list if strip_punct(w)]

        # sentence fixed parts may carry punctuation (kept as-is)
        sentence = rec['sentence']
        n_null = sum(1 for x in sentence if x is None)

        # re-group into spacing-based cards (RapidOCR), only if count still matches
        cards_for_this = cards.get(rec['image_file'])
        if cards_for_this:
            regrouped = regroup_answers(ans_list, cards_for_this)
            if len(regrouped) == n_null:
                ans_list = regrouped

        # skip broken questions: OCR failed (no options) -> answers don't fill the blanks
        if n_null == 0 or len(ans_list) != n_null:
            skipped += 1
            continue

        # options (draggable) = the same phrases, scrambled deterministically
        options = ans_list[:]
        rng.shuffle(options)
        if len(options) >= 2 and options == ans_list:
            options.reverse()

        q = {
            'prompt': rec['prompt'],
            'sentence': sentence,
            'options': options,
            'answers': ans_list,
        }

        sk = f"set_{rec['set_num']:02d}"
        if batch not in new_data:
            new_data[batch] = {'name': f'{batch} 真题', 'sets': {}}
        if sk not in new_data[batch]['sets']:
            new_data[batch]['sets'][sk] = {'name': f"第 {rec['set_num']} 套", 'questions': []}
        new_data[batch]['sets'][sk]['questions'].append(q)

    with open(DATA / 'questions_final.json', 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)

    nq = sum(len(s['questions']) for b in new_data for s in new_data[b]['sets'].values())
    # consistency check
    mismatches = 0
    for b in new_data:
        for s in new_data[b]['sets'].values():
            for q in s['questions']:
                n_null = sum(1 for x in q['sentence'] if x is None)
                if n_null != len(q['answers']) or n_null != len(q['options']):
                    mismatches += 1
    print(f'Merged: {nq} questions, {skipped} skipped (broken), {mismatches} null/answer mismatches')


if __name__ == '__main__':
    main()
