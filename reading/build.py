"""Build quiz.html (the reading practice site) from data/questions.json.

Flow: pick a set -> do each unit in order (a fill-in paragraph or a reading
passage with its questions) -> check answers immediately -> at the end, see
the total wrong count and elapsed time.

The data is embedded into the HTML as a JS object so the page is fully
self-contained (no server needed).
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / 'data'


def clean(text):
    if not text:
        return ''
    text = text.replace('�', '').strip()
    text = re.sub(r'[•◦○●·]', '', text)
    return text


def build_fill_in(unit):
    """Convert a fill-in unit into a clean renderable structure."""
    toks = unit['paragraph']
    blanks_by_idx = {b['token_index']: b for b in unit['blanks'] if b['token_index'] is not None}
    items = []
    for i, t in enumerate(toks):
        b = blanks_by_idx.get(i)
        if b is not None:
            items.append({'blank': True, 'prefix': b['prefix'], 'full': b['full'],
                          'q': b['q'], 'blank_len': b['blank_len'],
                          'inserted': bool(b.get('inserted'))})
        else:
            items.append({'text': clean(t)})
    return items


def build_question(q):
    out = {
        'q': q['q'],
        'prompt': clean(q['prompt']),
        'options': [clean(o) for o in q.get('options', [])],
        'answer': q.get('answer'),
        'kind': q.get('kind', 'detail'),
        'article': clean(q.get('article', '')),
    }
    if q.get('kind') == 'insert':
        out['squares'] = q.get('squares', [])
        out['answer_pos'] = q.get('answer_pos')
    return out


def main():
    questions = json.loads((DATA / 'questions.json').read_text(encoding='utf-8'))

    sets = {}
    for set_name, units in questions.items():
        out_units = []
        for u in units:
            if u['type'] == 'fill_in':
                out_units.append({'type': 'fill_in', 'items': build_fill_in(u)})
            else:
                out_units.append({
                    'type': 'passage',
                    'title': clean(u['title']),
                    'questions': [build_question(q) for q in u['questions']],
                })
        sets[set_name] = out_units

    data_js = json.dumps(sets, ensure_ascii=False)
    html = HTML_TEMPLATE.replace('__DATA__', data_js)
    out = ROOT / 'quiz.html'
    out.write_text(html, encoding='utf-8')
    print(f'Saved -> {out} ({len(sets)} sets, {sum(len(v) for v in sets.values())} units)')


HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>托福阅读练习</title>
<style>
  :root { --bg:#f5f6f8; --card:#fff; --ink:#1a1d23; --muted:#6b7280; --accent:#2563eb;
          --ok:#16a34a; --bad:#dc2626; --border:#e5e7eb; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,"PingFang SC","Microsoft YaHei",sans-serif;
         background:var(--bg); color:var(--ink); line-height:1.6; }
  header { background:var(--card); border-bottom:1px solid var(--border); padding:12px 20px;
           display:flex; align-items:center; gap:16px; flex-wrap:wrap; position:sticky; top:0; z-index:10; }
  header h1 { font-size:18px; margin:0; }
  select, button { font-size:14px; padding:8px 14px; border-radius:8px; border:1px solid var(--border);
                   background:#fff; cursor:pointer; }
  button.primary { background:var(--accent); color:#fff; border-color:var(--accent); }
  button:disabled { opacity:.5; cursor:not-allowed; }
  .timer { margin-left:auto; font-variant-numeric:tabular-nums; color:var(--muted); }
  main { max-width:860px; margin:0 auto; padding:24px 20px 80px; }
  .card { background:var(--card); border:1px solid var(--border); border-radius:12px;
          padding:20px 24px; margin-bottom:20px; }
  .unit-header { font-size:13px; color:var(--muted); margin-bottom:8px; }
  .unit-title { font-size:17px; font-weight:600; margin:0 0 12px; }
  .article { white-space:pre-wrap; background:#fafafa; border:1px solid var(--border);
             border-radius:8px; padding:14px 16px; margin:10px 0 16px; font-size:15px; }
  .fill-paragraph { font-size:16px; line-height:2.1; }
  .fill-paragraph .prefix { font-weight:700; }
  .fill-paragraph .blank-cell { display:inline-flex; flex-direction:column; align-items:center;
                                vertical-align:bottom; margin:0 2px; }
  .fill-paragraph .blank-count { font-size:10px; color:#9ca3af; line-height:1.3; }
  .fill-paragraph .blank-body { display:inline-flex; align-items:center; }
  .fill-paragraph input { width:5.2em; font-size:15px; padding:2px 6px; border:1px solid #cbd5e1;
                          border-radius:6px; text-align:center; margin:0 1px; }
  .fill-paragraph .blankdrop { color:var(--muted); font-size:12px; margin-left:2px; }
  .q-block { border-top:1px solid var(--border); padding-top:14px; margin-top:14px; }
  .q-prompt { font-weight:600; margin-bottom:8px; }
  .opt { display:block; padding:8px 12px; border:1px solid var(--border); border-radius:8px;
         margin-bottom:6px; cursor:pointer; font-size:15px; }
  .opt:hover { border-color:var(--accent); }
  .opt.sel { border-color:var(--accent); background:#eff6ff; }
  .opt.correct { border-color:var(--ok); background:#f0fdf4; }
  .opt.wrong { border-color:var(--bad); background:#fef2f2; }
  .opt .tag { font-weight:700; margin-right:8px; }
  .squares-line { display:flex; flex-wrap:wrap; gap:8px; margin:10px 0; }
  .sq { width:34px; height:34px; border:1px solid #cbd5e1; border-radius:8px; display:flex;
        align-items:center; justify-content:center; cursor:pointer; font-size:16px; }
  .sq.sel { border-color:var(--accent); background:#eff6ff; }
  .sq.correct { border-color:var(--ok); background:#f0fdf4; }
  .sq.wrong { border-color:var(--bad); background:#fef2f2; }
  .feedback { margin-top:14px; padding:12px 16px; border-radius:8px; font-size:15px; }
  .feedback.ok { background:#f0fdf4; color:#166534; }
  .feedback.bad { background:#fef2f2; color:#991b1b; }
  .stats { text-align:center; }
  .stats .big { font-size:34px; font-weight:700; }
  .hidden { display:none; }
  .set-grid { display:flex; flex-wrap:wrap; gap:10px; margin:20px 0; }
  .set-btn { padding:14px 20px; border-radius:10px; border:1px solid var(--border); background:#fff;
             cursor:pointer; font-size:16px; }
  .set-btn:hover { border-color:var(--accent); }
</style>
</head>
<body>
<header>
  <h1>托福阅读练习</h1>
  <button id="backBtn" onclick="backToSets()">选套</button>
  <span id="progress" class="timer"></span>
  <span id="timer" class="timer">⏱ 0:00</span>
</header>

<main id="main">
  <div class="card">
    <h2 class="unit-title">选择一套真题</h2>
    <p style="color:var(--muted)">每套 = 按题目出现顺序排列的若干「单位」（一篇填词 或 一篇阅读带若干题）。做完一个单位立刻对答案，整套结束后看总错题数与时耗。</p>
    <div id="setGrid" class="set-grid"></div>
  </div>
</main>

<script>
const SETS = __DATA__;
let state = null;

function $(id){ return document.getElementById(id); }

function renderSetGrid(){
  const g = $('setGrid');
  g.innerHTML = '';
  Object.keys(SETS).forEach(s => {
    const b = document.createElement('button');
    b.className = 'set-btn';
    b.textContent = s;
    b.onclick = () => startSet(s);
    g.appendChild(b);
  });
}

function startSet(setName){
  state = {
    setName,
    units: SETS[setName],
    unitIdx: 0,
    answers: [],   // per unit: array of user answers
    checked: [],   // per unit: bool
    startTime: Date.now(),
  };
  $('backBtn').classList.remove('hidden');
  renderUnit();
  tick();
}

function tick(){
  if(!state) return;
  const el = $('timer');
  const s = Math.floor((Date.now()-state.startTime)/1000);
  el.textContent = '⏱ ' + Math.floor(s/60) + ':' + String(s%60).padStart(2,'0');
  if(!state.finished) setTimeout(tick, 1000);
}

function renderUnit(){
  const u = state.units[state.unitIdx];
  const main = $('main');
  $('progress').textContent = state.setName + ' · ' + (state.unitIdx+1) + '/' + state.units.length;
  if(u.type === 'fill_in') renderFill(u, main);
  else renderPassage(u, main);
}

function renderFill(u, main){
  main.innerHTML = '<div class="card" id="unitCard"></div>';
  const card = $('unitCard');
  card.innerHTML = '<div class="unit-header">填词题 · 填入被抠掉的后半部分</div>'
    + '<div class="fill-paragraph" id="para"></div>'
    + '<div style="margin-top:18px"><button class="primary" onclick="checkUnit()">对答案</button></div>'
    + '<div id="feedback"></div>';
  const para = $('para');
  u.items.forEach((it, i) => {
    if(it.blank){
      const wrap = document.createElement('span');
      wrap.className = 'blank-cell';
      // small count label above the input box
      const cnt = document.createElement('span');
      cnt.className = 'blank-count';
      cnt.textContent = (it.blank_len || 1) + '字';
      wrap.appendChild(cnt);
      // body: visible prefix + input box
      const body = document.createElement('span');
      body.className = 'blank-body';
      if(it.prefix){
        const pre = document.createElement('span');
        pre.className = 'prefix';
        pre.textContent = it.prefix;
        body.appendChild(pre);
      }
      const inp = document.createElement('input');
      inp.type = 'text';
      inp.autocomplete = 'off';
      inp.dataset.idx = i;
      inp.dataset.blank = '1';
      inp.style.width = Math.max(2.2, (it.blank_len||3)+1) + 'em';
      body.appendChild(inp);
      if(it.inserted) {
        const d = document.createElement('span');
        d.className = 'blankdrop';
        d.title = '此空位置由答案补回，可能略有偏差';
        d.textContent = '·';
        body.appendChild(d);
      }
      wrap.appendChild(body);
      para.appendChild(wrap);
      para.appendChild(document.createTextNode(' '));
    } else {
      para.appendChild(document.createTextNode(' ' + it.text + ' '));
    }
  });
}

function renderPassage(u, main){
  main.innerHTML = '<div class="card" id="unitCard"></div>';
  const card = $('unitCard');
  let html = '<div class="unit-header">阅读题 · ' + u.questions.length + ' 题</div>'
    + '<h2 class="unit-title">' + esc(u.title) + '</h2>';
  u.questions.forEach((q, qi) => {
    html += '<div class="q-block">'
      + '<div class="q-prompt">' + q.q + '. ' + esc(q.prompt) + '</div>';
    if(q.kind === 'insert'){
      html += '<div class="article">' + esc(q.article) + '</div>'
        + '<div class="squares-line">';
      (q.squares||[]).forEach((sq, si) => {
        html += '<div class="sq" data-q="'+qi+'" data-sq="'+si+'">■</div>';
      });
      html += '</div>';
    } else {
      html += '<div class="article">' + esc(q.article) + '</div>';
      const letters = 'ABCD';
      (q.options||[]).forEach((o, oi) => {
        html += '<div class="opt" data-q="'+qi+'" data-opt="'+oi+'">'
          + '<span class="tag">'+letters[oi]+'.</span>' + esc(o) + '</div>';
      });
    }
    html += '</div>';
  });
  html += '<div style="margin-top:18px"><button class="primary" onclick="checkUnit()">对答案</button></div>'
    + '<div id="feedback"></div>';
  card.innerHTML = html;

  // attach listeners
  card.querySelectorAll('.opt').forEach(el => {
    el.onclick = () => {
      const qi = +el.dataset.q;
      card.querySelectorAll('.opt[data-q="'+qi+'"]').forEach(o => o.classList.remove('sel'));
      el.classList.add('sel');
    };
  });
  card.querySelectorAll('.sq').forEach(el => {
    el.onclick = () => {
      const qi = +el.dataset.q;
      card.querySelectorAll('.sq[data-q="'+qi+'"]').forEach(o => o.classList.remove('sel'));
      el.classList.add('sel');
    };
  });
}

function collectAnswers(){
  const u = state.units[state.unitIdx];
  const card = $('unitCard');
  if(u.type === 'fill_in'){
    const ans = [];
    card.querySelectorAll('input[data-blank]').forEach(inp => {
      ans.push(inp.value.trim().toLowerCase());
    });
    return ans;
  }
  const ans = [];
  u.questions.forEach((q, qi) => {
    if(q.kind === 'insert'){
      const sel = card.querySelector('.sq[data-q="'+qi+'"].sel');
      ans.push(sel ? (+sel.dataset.sq + 1) : null);   // position 1..n
    } else {
      const sel = card.querySelector('.opt[data-q="'+qi+'"].sel');
      ans.push(sel ? 'ABCD'[+sel.dataset.opt] : null);
    }
  });
  return ans;
}

function checkUnit(){
  const u = state.units[state.unitIdx];
  const card = $('unitCard');
  const answers = collectAnswers();
  let wrong = 0, detail = '';

  if(u.type === 'fill_in'){
    let ai = 0;
    card.querySelectorAll('input[data-blank]').forEach(inp => {
      const it = u.items[+inp.dataset.idx];
      const correct = it.full.toLowerCase();
      const user = inp.value.trim().toLowerCase();
      if(user === correct){ inp.style.borderColor = '#16a34a'; inp.style.background='#f0fdf4'; }
      else { inp.style.borderColor = '#dc2626'; inp.style.background='#fef2f2'; wrong++; }
      detail += '<div>· ' + esc(it.prefix) + '<b>' + esc(it.full.slice(it.prefix.length)) + '</b>'
        + (user===correct ? '' : ' （你填了 ' + esc(user||'空') + '）') + '</div>';
    });
  } else {
    const letters = 'ABCD';
    u.questions.forEach((q, qi) => {
      const user = answers[qi];
      const correct = normalizeAnswer(q);
      const ok = (user !== null && String(user) === String(correct));
      if(!ok) wrong++;
      if(q.kind === 'insert'){
        card.querySelectorAll('.sq[data-q="'+qi+'"]').forEach(el => {
          const pos = +el.dataset.sq + 1;
          if(pos === correct) el.classList.add('correct');
          else if(pos === user) el.classList.add('wrong');
        });
      } else {
        card.querySelectorAll('.opt[data-q="'+qi+'"]').forEach(el => {
          const letter = letters[+el.dataset.opt];
          if(letter === correct) el.classList.add('correct');
          else if(letter === user) el.classList.add('wrong');
        });
      }
      detail += '<div>· Q' + q.q + '：正确答案 <b>' + esc(String(correct)) + '</b></div>';
    });
  }

  const fb = $('feedback');
  const total = u.type==='fill_in' ? u.items.filter(x=>x.blank).length : u.questions.length;
  fb.innerHTML = '<div class="feedback ' + (wrong===0?'ok':'bad') + '">'
    + (wrong===0 ? '✓ 全部正确！' : '✗ 错 ' + wrong + ' / ' + total + ' 题')
    + '<div style="font-size:14px;margin-top:8px">' + detail + '</div>'
    + '<div style="margin-top:12px"><button class="primary" onclick="nextUnit()">'
    + (state.unitIdx < state.units.length-1 ? '下一题' : '查看统计') + '</button></div></div>';
}

function normalizeAnswer(q){
  if(q.kind === 'insert') return q.answer_pos;   // already a position 1..4
  return q.answer;
}

function nextUnit(){
  if(state.unitIdx < state.units.length - 1){
    state.unitIdx++;
    renderUnit();
  } else {
    showStats();
  }
}

function showStats(){
  state.finished = true;
  const main = $('main');
  main.innerHTML = '<div class="card stats"><div class="unit-header">' + state.setName + ' · 完成</div>'
    + '<div class="big">🎉</div>'
    + '<p>用时 <b>' + $('timer').textContent.replace('⏱ ','') + '</b></p>'
    + '<p>共 <b>' + state.units.length + '</b> 个单位</p>'
    + '<div style="margin-top:16px"><button class="primary" onclick="backToSets()">再选一套</button></div></div>';
}

function backToSets(){
  state = null;
  $('backBtn').classList.add('hidden');
  $('progress').textContent = '';
  $('timer').textContent = '⏱ 0:00';
  const main = $('main');
  main.innerHTML = '<div class="card"><h2 class="unit-title">选择一套真题</h2>'
    + '<p style="color:var(--muted)">每套 = 按题目出现顺序排列的若干「单位」（一篇填词 或 一篇阅读带若干题）。做完一个单位立刻对答案，整套结束后看总错题数与时耗。</p>'
    + '<div id="setGrid" class="set-grid"></div></div>';
  renderSetGrid();
}

function esc(s){ return (s||'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

renderSetGrid();
</script>
</body>
</html>
'''


if __name__ == '__main__':
    main()
