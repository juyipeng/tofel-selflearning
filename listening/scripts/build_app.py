#!/usr/bin/env python
"""Build a self-contained HTML practice app for the 3.22A listening set.

- Slices per-passage audio clips (mp3), embeds them as base64 data URIs.
- 14 sets: 2 x "Listen and Response" + 12 x "Listen and Choose".
- Linear test flow (play once, no back), then 对答案 with replay allowed.
- File-based save/load of progress (no localStorage); home shows last wrong count.
"""
import base64
import json
import os
import subprocess

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(HERE, "processed", "manifest.json")
WAV = os.path.join(HERE, "processed", "3.22A_full.wav")
APP_DIR = os.path.join(HERE, "app")
CLIP_DIR = os.path.join(APP_DIR, "clips")

PRE = 0.3
POST = 0.5

KIND_LABEL = {"conversation": "对话", "announcement": "通知", "talk": "讲座"}


def slice_clips(manifest):
    os.makedirs(CLIP_DIR, exist_ok=True)
    dur = manifest["audio_duration"]
    for p in manifest["passages"]:
        a = p["audio"]
        start = max(0.0, a["start"] - PRE)
        end = min(dur, a["end"] + POST)
        out = os.path.join(CLIP_DIR, f"{p['id']}.mp3")
        cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{start:.3f}",
               "-to", f"{end:.3f}", "-i", WAV, "-ar", "44100", "-ac", "1",
               "-b:a", "64k", out]
        subprocess.run(cmd, check=True)


def build_sets(manifest):
    passages = manifest["passages"]
    sets = []
    for mod in (1, 2):
        resp = [p for p in passages if p["module"] == mod and p["type"] == "choose_response"]
        if not resp:
            continue
        steps = []
        for p in resp:
            q = p["questions"][0]
            steps.append({"no": q["no"], "statement": p["stimulus"],
                          "audio": f"clips/{p['id']}.mp3",
                          "options": q["options"], "answer": q["answer"]})
        sets.append({"id": f"resp{mod}", "type": "response", "module": mod,
                     "title": "Listen and Response",
                     "sub": f"Module {mod} · {len(steps)} 小题", "steps": steps})
    for p in passages:
        if p["type"] == "choose_response":
            continue
        sets.append({"id": p["id"], "type": "choose", "module": p["module"],
                     "title": "Listen and Choose",
                     "kind": KIND_LABEL.get(p["type"], p["type"]),
                     "sub": f"Module {p['module']} · {p['section']} · {len(p['questions'])} 小题",
                     "audio": f"clips/{p['id']}.mp3",
                     "stimulus": p["stimulus"],
                     "steps": [{"no": q["no"], "prompt": q["prompt"],
                                "options": q["options"], "answer": q["answer"]}
                               for q in p["questions"]]})
    return sets


def data_uri(rel_path):
    with open(os.path.join(APP_DIR, rel_path), "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:audio/mpeg;base64,{b64}"


def embed_audio(sets):
    for s in sets:
        if s["type"] == "choose":
            s["audio"] = data_uri(s["audio"])
        else:
            for it in s["steps"]:
                it["audio"] = data_uri(it["audio"])


HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__</title>
<style>
  :root { --bg:#f4f5f7; --card:#fff; --ink:#1c2333; --muted:#6b7280;
         --accent:#4f46e5; --accent2:#eef2ff; --ok:#16a34a; --bad:#dc2626; --line:#e5e7eb; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
         background:var(--bg); color:var(--ink); }
  .wrap { max-width:960px; margin:0 auto; padding:28px 20px 60px; }
  h1.title { font-size:22px; margin:0 0 4px; }
  .subtitle { color:var(--muted); font-size:13px; margin-bottom:16px; }
  .toolbar { display:flex; gap:10px; margin-bottom:8px; }
  .toolbar button { background:var(--card); border:1px solid var(--line); border-radius:9px;
          padding:8px 14px; cursor:pointer; font-size:13.5px; color:var(--ink); }
  .toolbar button:hover { border-color:var(--accent); color:var(--accent); }
  .modh { font-size:13px; font-weight:700; color:var(--muted); text-transform:uppercase;
          letter-spacing:.04em; margin:22px 0 10px; }
  .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:14px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:14px;
          padding:16px 18px; cursor:pointer; transition:.12s; position:relative; }
  .card:hover { border-color:var(--accent); box-shadow:0 4px 16px rgba(79,70,229,.10); }
  .card .badge { display:inline-block; font-size:11px; font-weight:700; padding:3px 9px;
          border-radius:20px; margin-bottom:8px; }
  .badge.resp { background:#fef3c7; color:#b45309; }
  .badge.choose { background:var(--accent2); color:var(--accent); }
  .card h3 { font-size:15px; margin:0 0 4px; }
  .card .sub { font-size:12.5px; color:var(--muted); }
  .card .last { font-size:12.5px; font-weight:700; color:var(--bad); margin-top:8px; }
  .card .done { position:absolute; top:14px; right:16px; color:var(--ok); font-size:18px; font-weight:700; }

  .test-head { display:flex; align-items:center; gap:12px; margin-bottom:6px; }
  .back { background:var(--card); border:1px solid var(--line); border-radius:8px;
          padding:7px 12px; cursor:pointer; font-size:13px; }
  .back:hover { background:#f3f4f6; }
  .test-head .t { font-size:18px; font-weight:700; flex:1; }
  .progress { height:5px; background:var(--line); border-radius:3px; margin:10px 0 22px; overflow:hidden; }
  .progress .bar { height:100%; background:var(--accent); transition:width .2s; }
  .step-label { color:var(--muted); font-size:13px; margin-bottom:14px; }

  .play-btn { display:inline-flex; align-items:center; gap:8px; font-size:16px; font-weight:600;
          padding:13px 26px; border:0; border-radius:12px; background:var(--accent); color:#fff;
          cursor:pointer; }
  .play-btn:disabled { background:#c7c9d1; cursor:not-allowed; }
  .play-btn.small { padding:9px 18px; font-size:14px; }
  .play-btn.replay { background:var(--card); color:var(--accent); border:1px solid var(--accent); }
  .play-hint { color:var(--muted); font-size:13px; margin-top:8px; }

  .q-card { background:var(--card); border:1px solid var(--line); border-radius:14px;
            padding:20px 22px; margin-top:16px; }
  .q-card .qn { font-weight:700; font-size:15px; margin-bottom:8px; }
  .q-card .qn .n { color:var(--accent); margin-right:8px; }
  .q-card .prompt { font-size:15px; line-height:1.6; margin-bottom:14px; }
  .opt { display:flex; align-items:flex-start; gap:10px; padding:10px 12px; border-radius:9px;
         cursor:pointer; border:1px solid transparent; }
  .opt:hover { background:#f3f4f6; }
  .opt input { margin-top:3px; }
  .opt .letter { font-weight:700; color:var(--muted); min-width:22px; }
  .opt.sel { background:var(--accent2); border-color:var(--accent); }
  .opt.correct { background:#e8f7ee; border-color:var(--ok); }
  .opt.wrong { background:#fdeaea; border-color:var(--bad); }
  .verdict { margin-top:12px; font-weight:700; font-size:14px; }
  .verdict.ok { color:var(--ok); } .verdict.bad { color:var(--bad); }

  .footer { display:flex; justify-content:space-between; align-items:center; margin-top:24px; }
  .next-btn { font-size:15px; font-weight:600; padding:11px 28px; border:0; border-radius:10px;
          background:var(--accent); color:#fff; cursor:pointer; }
  .next-btn:disabled { background:#c7c9d1; cursor:not-allowed; }

  .transcript { background:var(--card); border:1px solid var(--line); border-radius:12px;
                padding:14px 18px; margin-top:18px; font-size:14px; line-height:1.7;
                white-space:pre-wrap; }
  .transcript .spk { color:var(--accent); font-weight:700; }
  .score-banner { background:var(--card); border:1px solid var(--line); border-radius:12px;
                  padding:14px 18px; margin-top:16px; font-weight:700; font-size:15px; }
  .score-banner .n { color:var(--accent); }
  .replay-row { margin-top:14px; }
</style>
</head>
<body>
<div class="wrap">
  <div id="view"></div>
</div>
<audio id="player" preload="auto"></audio>
<script>
const DATA = __DATA__;
const sets = DATA.sets;

let cur = null, step = 0, phase = 'intro';
let answers = {}, introPlayed = false, itemPlayed = {};
let results = {};   // set_id -> { wrong, total, ts }

const $ = id => document.getElementById(id);
const player = $('player');

function esc(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function fmtStim(s){ return esc(s).replace(/^(Man|Woman|Narrator):/gm,'<span class="spk">$1:</span>'); }
function showError(msg){ const el=$('audioErr'); if(el) el.innerHTML='<div style="color:var(--bad);font-weight:700;margin-top:10px">⚠ '+msg+'</div>'; }
function playOnce(src,onEnd){ player.onerror=()=>showError('音频加载失败'); player.src=src; player.onended=onEnd||null; player.play().then(()=>{}).catch(e=>showError('播放失败：'+(e&&e.message?e.message:e))); }
function replay(src){ player.onerror=()=>showError('音频加载失败'); player.src=src; player.onended=null; player.play().then(()=>{}).catch(e=>showError('播放失败：'+(e&&e.message?e.message:e))); }

/* ---------- HOME ---------- */
function renderHome(){
  const by = {};
  sets.forEach(s => (by[s.module] = by[s.module]||[]).push(s));
  let h = `<h1 class="title">${esc(DATA.title)}</h1>
    <div class="subtitle">共 ${sets.length} 套题 · 对答案前不可重听、不可回退 · 进度可通过「保存/加载」导出成文件</div>
    <div class="toolbar">
      <button onclick="saveState()">💾 保存进度</button>
      <button onclick="loadState()">📂 加载进度</button>
    </div>`;
  for (const [m, list] of Object.entries(by)) {
    h += `<div class="modh">Module ${m}</div><div class="grid">`;
    list.forEach(s => {
      const badge = s.type==='response'
        ? `<span class="badge resp">Listen &amp; Response</span>`
        : `<span class="badge choose">Listen &amp; Choose · ${esc(s.kind)}</span>`;
      const r = results[s.id];
      const done = r ? '<div class="done">✓</div>' : '';
      const last = r ? `<div class="last">上次错 ${r.wrong} / ${r.total} 题</div>` : '';
      h += `<div class="card" onclick="startSet('${s.id}')">${badge}${done}
              <h3>${esc(s.title)}</h3><div class="sub">${esc(s.sub)}</div>${last}</div>`;
    });
    h += `</div>`;
  }
  $('view').innerHTML = h;
}

/* ---------- SAVE / LOAD (file-based, no localStorage) ---------- */
function saveState(){
  const data = { saved_at: new Date().toISOString(), results: results };
  const blob = new Blob([JSON.stringify(data, null, 2)], {type:'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'toefl_progress.json'; a.click();
  URL.revokeObjectURL(url);
}
function loadState(){
  const input = document.createElement('input');
  input.type = 'file'; input.accept = '.json,application/json';
  input.onchange = e => {
    const f = e.target.files[0]; if (!f) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const data = JSON.parse(reader.result);
        results = data.results || {};
        renderHome();
      } catch(err) { alert('加载失败：文件格式不正确'); }
    };
    reader.readAsText(f);
  };
  input.click();
}

/* ---------- START / TEST FLOW ---------- */
function startSet(id){
  cur = sets.find(s => s.id===id);
  step = 0; phase = (cur.type==='choose') ? 'intro' : 'question';
  answers = {}; introPlayed = false; itemPlayed = {};
  render();
}
function goHome(){ cur=null; renderHome(); }
function totalSteps(){ return cur.steps.length; }

function render(){
  if (!cur) { renderHome(); return; }
  if (phase === 'result') { renderResult(); return; }

  const steps = cur.steps;
  const total = steps.length;
  const prog = phase==='intro' ? 0 : ((step+1)/total*100);
  let body = '';

  if (phase === 'intro') {
    body = `
      <div class="step-label">先听完整段音频，再逐题作答（只能播放一次）</div>
      <button class="play-btn" id="introPlay" onclick="doIntroPlay()">▶ 播放音频</button>
      <div class="play-hint">播放结束后自动进入第 1 题</div>`;
  } else {
    const s = steps[step];
    const isResp = cur.type==='response';
    const sel = answers[step] || null;
    const opts = s.options.map((o,i)=>{
      const letter = 'ABCD'[i];
      return `<label class="opt${sel===letter?' sel':''}">
        <input type="radio" name="opt" value="${letter}" ${sel===letter?'checked':''} onchange="choose('${letter}')">
        <span class="letter">${letter}.</span><span>${esc(o)}</span></label>`;
    }).join('');
    let playBtn = '';
    if (isResp) {
      const played = itemPlayed[step];
      playBtn = `<button class="play-btn small" ${played?'disabled':''} onclick="doItemPlay()">
          ${played?'已播放':'▶ 播放'}</button>`;
    }
    const prompt = isResp ? 'Choose the best response.' : s.prompt;
    body = `
      <div class="q-card">
        ${playBtn}
        <div class="qn"><span class="n">#${s.no}</span></div>
        ${prompt ? `<div class="prompt">${esc(prompt)}</div>` : ''}
        ${opts}
      </div>`;
  }

  const canNext = phase!=='intro' && !!answers[step];
  const lastStep = phase!=='intro' && step===total-1;
  const nextLabel = lastStep ? '对答案' : '下一题';

  $('view').innerHTML = `
    <div class="test-head">
      <button class="back" onclick="goHome()">← 返回</button>
      <div class="t">${esc(cur.title)}${cur.kind?(' · '+esc(cur.kind)):''}</div>
      <div style="color:var(--muted);font-size:13px">${esc(cur.sub)}</div>
    </div>
    <div class="progress"><div class="bar" style="width:${prog}%"></div></div>
    <div class="step-label">${phase==='intro' ? '准备' : `第 ${step+1} / ${total} 题`}</div>
    ${body}
    <div id="audioErr"></div>
    <div class="footer">
      <span></span>
      ${phase==='intro' ? '' : `<button class="next-btn" ${canNext?'':'disabled'} onclick="${lastStep?'doCheck()':'next()'}">${nextLabel}</button>`}
    </div>`;
}

function doIntroPlay(){
  const b = $('introPlay'); if (b) b.disabled = true;
  playOnce(cur.audio, () => { phase='question'; render(); });
}
function doItemPlay(){
  if (itemPlayed[step]) return;
  itemPlayed[step] = true;
  const b = document.querySelector('.play-btn.small'); if (b) b.disabled = true;
  playOnce(cur.steps[step].audio, null);
}
function choose(letter){ answers[step] = letter; render(); }
function next(){ if (step < totalSteps()-1){ step++; render(); } }

/* ---------- RESULT (对答案, replay allowed) ---------- */
function doCheck(){
  phase = 'result';
  const steps = cur.steps;
  let correct = 0;
  steps.forEach((s,i)=>{ if (answers[i]===s.answer) correct++; });
  results[cur.id] = { wrong: steps.length - correct, total: steps.length,
                      ts: new Date().toISOString() };
  render();
}

function renderResult(){
  const steps = cur.steps;
  const isResp = cur.type==='response';
  const r = results[cur.id] || {};
  let correct = (r.total||steps.length) - (r.wrong||0);

  let html = `
    <div class="test-head">
      <button class="back" onclick="goHome()">← 返回</button>
      <div class="t">${esc(cur.title)}${cur.kind?(' · '+esc(cur.kind)):''} — 结果</div>
    </div>
    <div class="score-banner">答对 <span class="n">${correct}</span> / ${r.total||steps.length} 题 · 错 <span class="n" style="color:var(--bad)">${r.wrong||0}</span> 题</div>`;

  if (cur.type==='choose') {
    html += `<div class="replay-row"><button class="play-btn small replay" onclick="replay(cur.audio)">▶ 重放音频</button></div>
      <div class="transcript">${fmtStim(cur.stimulus)}</div>`;
  }

  steps.forEach((s,i)=>{
    const sel = answers[i] || null;
    const ok = sel===s.answer;
    const opts = s.options.map((o,k)=>{
      const letter='ABCD'[k];
      let cls='opt';
      if (letter===s.answer) cls+=' correct';
      else if (sel===letter) cls+=' wrong';
      return `<div class="${cls}"><span class="letter">${letter}.</span><span>${esc(o)}</span></div>`;
    }).join('');
    const v = ok
      ? `<div class="verdict ok">✓ 正确</div>`
      : `<div class="verdict bad">✗ 你的选择：${sel||'未作答'} · 正确答案：${s.answer}</div>`;
    const head = isResp
      ? `<div class="qn"><span class="n">#${s.no}</span> ${esc(s.statement)}</div>`
      : `<div class="qn"><span class="n">#${s.no}</span> ${esc(s.prompt)}</div>`;
    const rp = isResp ? `<div class="replay-row"><button class="play-btn small replay" onclick="replay(cur.steps[${i}].audio)">▶ 重放这句</button></div>` : '';
    html += `<div class="q-card">${head}${rp}${opts}${v}</div>`;
  });
  $('view').innerHTML = html;
}

renderHome();
</script>
</body>
</html>
"""


def main():
    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    print("Slicing audio clips ...")
    slice_clips(manifest)

    sets = build_sets(manifest)
    n_q = sum(len(s["steps"]) for s in sets)
    print(f"sets: {len(sets)}  (response: {sum(1 for s in sets if s['type']=='response')}, "
          f"choose: {sum(1 for s in sets if s['type']=='choose')})  total items/questions: {n_q}")

    print("Embedding audio as base64 (single-file) ...")
    embed_audio(sets)

    payload = {"title": manifest["title"], "sets": sets}
    html = HTML.replace("__TITLE__", manifest["title"]) \
               .replace("__DATA__", json.dumps(payload, ensure_ascii=False))

    out = os.path.join(APP_DIR, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    size_mb = os.path.getsize(out) / 1024 / 1024
    print(f"Saved {out}  ({size_mb:.1f} MB, self-contained)")
    print("Done.")


if __name__ == "__main__":
    main()
