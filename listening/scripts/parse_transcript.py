#!/usr/bin/env python
"""Parse the 3.22A transcript docx + answer key into structured JSON.

Output: processed/transcript_structured.json
  {title, date, modules: [{no, name, passages: [{id, section, type,
      stimulus, questions: [{no, prompt, options[], answer}]}]}]}
"""
import docx
import json
import re

SRC = "raw-data/3月（有文本）/3.22 A/3月22A日真题答案+文本.docx"
KEY = "raw-data/3月（有文本）/3.22 A/3.22A 听力答案.docx"
OUT = "processed/transcript_structured.json"

# Answer key (lowercase letters) — from 3.22A 听力答案.docx
MOD1_ANS = "1c 2b 3d 4b 5a 6b 7a 8c 9d 10a 11a 12b 13c 14d 15a 16b 17c 18a 19b 20d 21c 22d 23a 24b 25b 26b 27b 28c 29b 30c 31b 32d"
MOD2_ANS = "1d 2d 3d 4c 5d 6b 7c 8c 9d 10a 11c 12a 13d 14b 15c"


def parse_answers(s):
    return {int(m.group(1)): m.group(2).upper()
            for m in re.finditer(r"(\d+)\s*([a-dA-D])", s)}


ANSWERS = {}
ANSWERS.update(parse_answers(MOD1_ANS))
ANSWERS.update({k: v for k, v in parse_answers(MOD2_ANS).items() if k not in ANSWERS})

# Module 2 answers share keys 1..15 with Module 1's 1..15! Handle by module.
# parse_answers(MOD2_ANS) gives 1..15; Module 1 also has 1..32. Collision.
# So store answers per-module instead.
MOD1 = parse_answers(MOD1_ANS)
MOD2 = parse_answers(MOD2_ANS)

SECTION_RE = re.compile(r"^Q(\d+)-Q?(\d+)\s+(.*)$")
QUESTION_RE = re.compile(r"^Question\s+(\d+)\s*:?\s*(.*)$")
OPT_PREFIX_RE = re.compile(r"^[A-D]\s*[\.\)]\s*")

TYPE_MAP = {
    "Listen and Choose a Response": "choose_response",
    "Listen to a Conversation": "conversation",
    "Listen to a school radio announcement": "announcement",
    "Listen to an Announcement": "announcement",
    "Listen to a talk in": "talk",
    "Listen to a talk on": "talk",
}


def classify(section_text):
    for key, typ in TYPE_MAP.items():
        if key in section_text:
            return typ
    return "talk"


def main():
    d = docx.Document(SRC)
    # flatten paragraphs -> text lines (paragraphs can embed \n speaker turns)
    lines = []
    for p in d.paragraphs:
        t = p.text.strip()
        if not t:
            continue
        for sub in t.split("\n"):
            sub = sub.strip()
            if sub:
                lines.append(sub)

    modules = []
    cur_module = None
    cur_passage = None
    cur_question = None

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        # Module header
        m = re.match(r"^Module\s+(\d+)", line)
        if m and "Listen" not in line:
            cur_module = {"no": int(m.group(1)), "name": line, "passages": []}
            modules.append(cur_module)
            cur_passage = None
            cur_question = None
            i += 1
            continue

        # Section header  e.g. "Q13-Q14 Listen to a Conversation"
        m = SECTION_RE.match(line)
        if m and "Listen" in line:
            start_q = int(m.group(1))
            end_q = int(m.group(2)) if m.group(2) else start_q
            section = m.group(3)
            typ = classify(section)
            cur_passage = {
                "section": f"Q{start_q}-Q{end_q}",
                "type": typ,
                "stimulus_lines": [],
                "questions": [],
            }
            cur_module["passages"].append(cur_passage)
            cur_question = None
            i += 1
            continue

        # Question marker
        m = QUESTION_RE.match(line)
        if m:
            qno = int(m.group(1))
            rest = m.group(2).strip()
            cur_question = {"no": qno, "prompt": rest or None, "options": []}
            cur_passage["questions"].append(cur_question)
            # If the prompt is embedded in the Question line (choose-response),
            # it is already set. Otherwise it will be filled by the next line.
            i += 1
            continue

        # Now line is either: a prompt (next line after "Question N"), an option,
        # or stimulus content.
        if cur_question is not None:
            # fill prompt if empty, else treat as option
            if cur_question["prompt"] is None:
                cur_question["prompt"] = line
            else:
                cur_question["options"].append(line)
            i += 1
            continue

        # otherwise: stimulus content (inside a passage section, before questions)
        if cur_passage is not None:
            cur_passage["stimulus_lines"].append(line)
            i += 1
            continue

        # nothing matched (title etc.)
        i += 1

    # ---- post-process: assign answers, build stimulus text ----
    for mod in modules:
        ans_map = MOD1 if mod["no"] == 1 else MOD2
        for psg in mod["passages"]:
            # stimulus: drop the narrator "Listen to ..." line, keep the rest
            stim = []
            for ln in psg["stimulus_lines"]:
                if ln.lower().startswith("listen to a") or ln.lower().startswith("listen to the"):
                    continue  # narrator instruction
                stim.append(ln)
            psg.pop("stimulus_lines")
            psg["stimulus"] = "\n".join(stim).strip()
            # questions: strip option prefixes, attach answers
            for q in psg["questions"]:
                q["options"] = [OPT_PREFIX_RE.sub("", o).strip() for o in q["options"]]
                q["answer"] = ans_map.get(q["no"])

    result = {
        "title": "3.22A 听力真题",
        "date": "3.22A",
        "audio_file": "raw-data/3月（有文本）/3.22 A/3.22A 听力.m4a",
        "modules": modules,
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"Saved {OUT}")
    return result


if __name__ == "__main__":
    r = main()
    total_q = sum(len(q["questions"]) for m in r["modules"] for q in m["passages"])
    print("modules:", len(r["modules"]), "| passages:",
          sum(len(m["passages"]) for m in r["modules"]), "| questions:", total_q)
    # quick sanity: print per-passage summary
    for m in r["modules"]:
        print(f"\n=== {m['name']} ===")
        for p in m["passages"]:
            qs = [q["no"] for q in p["questions"]]
            print(f"  {p['section']:8s} {p['type']:15s} Q{qs} "
                  f"stimulus={len(p['stimulus'])}ch")
