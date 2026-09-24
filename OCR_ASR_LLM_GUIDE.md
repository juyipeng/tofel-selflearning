# 多模态内容处理方案（OCR / ASR / LLM）

> 下面代码块是**方法示意**。实际实现已收敛到 [`shared/ocr.py`](shared/ocr.py)（本地 GLM-OCR 调用），
> 各模块的解析逻辑仍留在各自脚本里。

本文档记录本 TOEFL 学习项目中「把图片、音频、文字变成结构化刷题数据」的三类做法，供以后复用：

1. **本地 OCR**：用 Ollama 跑 GLM-OCR 视觉模型识别题目图片里的文字。
2. **大批量文字任务**：用 DeepSeek API（langchain）做结构化批量处理（如组词排序），替代派大量 agent。
3. **音频转文字 + 对齐到题目**：用 faster-whisper 做听力 ASR 转写 + 强制对齐，把一条连续音频切成每道题对应的一段。

---

## 一、本地 OCR（GLM-OCR via Ollama）

### 为什么用本地 OCR

- 阿里云 OCR 有配额限制（跑一批题就 403 用尽）。
- GLM-OCR（0.9B）是智谱专门做 OCR 的小模型，本地跑无配额、词边界准（不会把 `have been updated` 拼成 `havebeenupdated`）。

### 安装与拉取模型

```bash
ollama pull glm-ocr:q8_0   # 约 1.6 GB，q8_0 量化版
```

### 调用方式

脚本见 `ocr_glm.py`，核心是 Ollama 原生 `/api/generate` 接口（视觉模型别走 OpenAI 兼容接口）：

```python
import json, base64, io
from urllib.request import Request, urlopen
from PIL import Image

def ocr_image(img_path, prompt):
    im = Image.open(img_path).convert('RGB')
    w, h = im.size
    # 关键：GLM-OCR 对超宽图（>1600px）会识别失败，先缩小
    if w > 1600:
        im = im.resize((1600, max(1, int(h * 1600 / w))))
    buf = io.BytesIO(); im.save(buf, format='JPEG')
    b64 = base64.b64encode(buf.getvalue()).decode()
    body = {'model': 'glm-ocr:q8_0', 'prompt': prompt, 'images': [b64], 'stream': False}
    req = Request('http://localhost:11434/api/generate',
                  json.dumps(body).encode(), {'Content-Type': 'application/json'})
    return json.loads(urlopen(req, timeout=600).read()).get('response', '')
```

### 提示词（重要经验）

**用简单提示词，不要用「结构化 3 段式」提示词**。结构化提示词会让 0.9B 的小模型变笨（约 28% 出错）。

- ✅ 简单（默认行为，版面读得准）：
  ```
  Transcribe all the text in this image, preserving line breaks and layout.
  ```
- ❌ 结构化（容易漏句子或漏选项）：
  ```
  Output exactly 3 parts: prompt / sentence with ___ / candidate words...
  ```

> 只有对「漏读」的异常图重跑时，才用更明确的提示词点明三个部分：
> ```
> This is a TOEFL "make a sentence" question. It has THREE parts stacked vertically:
> 1. top: a prompt sentence  2. middle: a target sentence with blank underline slots
> 3. bottom: candidate words. Use ___ for each blank. Put the candidate words last.
> ```

### 输出与解析

简单提示词下，GLM-OCR 输出三块（用空行分隔）：

```
The professor announced a change in the syllabus.

____ ____ know ____ ____ ____ ?
do have been updated the due dates if you
```

解析规则（见 `ocr_glm.py` 的 `parse()`）：

- **第一非空行** = 提示句 prompt。
- **最后一非空行** = 待选词 options（空格分词）。
- **中间部分** = 待填句，把下划线 `____` 换成空位 null。

```python
import re
def parse(text):
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    prompt = lines[0]
    options = lines[-1].split()
    mid = re.sub(r'_+', ' _BLANK_ ', ' '.join(lines[1:-1]))
    sentence = [None if t == '_BLANK_' else t for t in mid.split()]
    return prompt, sentence, options
```

### 常见坑

| 问题 | 现象 | 解决 |
|---|---|---|
| 超宽图读不出 | 返回 `text.` 占位符或空 | 宽 >1600px 时先缩小再 OCR |
| 结构化提示词 | 句子/选项串行、漏读 | 用简单提示词 |
| 个别图仍漏读 | 缺句子或缺选项 | 用「三部分」明确提示词重跑（`reocr_abnormal.py`） |

---

## 二、用 API 做大批量文字任务（DeepSeek + langchain）

### 场景

要把 1000+ 道题「打散的词重组排序」这类任务，用「派 28 个 agent」既慢又受并发上限（20）限制。更简单：**写一个脚本，拼好上下文 + 提示词，让 LLM 一次性结构化批量输出，再解析 JSON**。

### 环境与配置

- 环境：`E:/conda_envs/chat`（已装 `langchain`、`langchain_openai`、`openai`）。
- DeepSeek 是 OpenAI 兼容格式，直接用 `ChatOpenAI`：

```python
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(
    base_url='https://api.deepseek.com',   # 没有 /v1
    api_key='sk-...',
    model='deepseek-v4-flash',
    temperature=0,
    request_timeout=1800,   # 大批量输出慢，超时要设大
    max_retries=2,
)
```

### 提示词设计：结构化批量输出

要点：**把「规则 + 输入 JSON 数组」拼成一个 user 消息，要求只输出 JSON 数组，禁止解释和 markdown 代码块**。示例见 `llm_order.py`：

```python
SYSTEM = '你是英文造句题解析器。给定 JSON 数组每题 {p,s,o}……输出 answers 数组。'

def build_prompt(questions):
    return (
        '对每道题输出 {"answers":[...]}。规则：……\n'
        '严格按输入顺序，只输出一个 JSON 数组，不要解释、不要代码块。\n\n'
        '输入：\n' + json.dumps(questions, ensure_ascii=False)
    )
```

### 解析输出

LLM 输出可能带 markdown 围栏，用「找第一个 `[` 到最后一个 `]`」的方式稳健解析：

```python
def extract_json(text):
    text = re.sub(r'```[a-zA-Z]*', '', text).strip()
    s, e = text.find('['), text.rfind(']')
    return json.loads(text[s:e+1]) if s != -1 and e > s else None
```

### 完整批量脚本

见 `llm_order.py`。核心循环：

```python
for f in todo_batches:
    data = process_batch(f, llm)          # 调 API + 解析
    json.dump(data, open(result_file, 'w', encoding='utf-8'), ensure_ascii=False)
```

### 常见坑

| 问题 | 现象 | 解决 |
|---|---|---|
| 慢 | deepseek-v4-flash 有推理开销，5 题约 160s | 大批量分小批并行；`request_timeout` 设大 |
| 输出带围栏/解释 | JSON 前有 ```json | `extract_json` 去掉围栏再找 `[...]` |
| 输出长度对不上 | 漏题/多题 | 校验 `len(data) == len(questions)`，失败重试 |
| 大小写被改写 | 模型把 `do` 改成 `Do` | 下游用大小写不敏感比较兜底 |

---

## 三、音频转文字 + 对齐到题目（听力 ASR）

### 场景

TOEFL 听力真题：一条 26 分钟连续音频，串着几十道题。要做「刷题 app」，需要：

1. 把一条音频切成「每道题/每段材料对应的一段」；
2. 每道题有题目、选项、答案、听力原文。

### 关键思路：有文本就用「强制对齐」，不做「从头听写」

- 3 月那套题 docx 里**已经有完整逐字稿**（题目 + 原文 + 答案都是文字）。
- 所以不需要 ASR 去「听懂」音频说了什么，只需要知道**每个词出现在第几秒**——这就是**强制对齐（forced alignment）**，比从头听写准得多。
- 做法：faster-whisper 转写拿「词级时间戳」，再用 difflib 把已知文本对齐到时间戳上，得到每题/每段的起止秒。

### 环境与安装

- 环境：`E:/conda_envs/pytorch`（torch 2.4.1 + CUDA，GPU 为 RTX 3060 6GB）。
- `pip install faster-whisper`（自带 ctranslate2，不依赖 torch，但装在 pytorch 环境方便）。
- 运行前要设 `KMP_DUPLICATE_LIB_OK=TRUE`，否则 torch 和 onnxruntime 的 OpenMP 冲突直接崩。

### 转写（词级时间戳）

脚本 `listening/scripts/transcribe.py`，核心：

```python
from faster_whisper import WhisperModel
model = WhisperModel('large-v3', device='cuda', compute_type='int8_float16')
segments, info = model.transcribe(wav, language='en', word_timestamps=True, vad_filter=True)
for seg in segments:
    for w in seg.words:   # w.word / w.start / w.end / w.probability
        ...
```

- 6GB 显存跑 `large-v3` int8 没问题，26 分钟音频约 5 分钟转完。
- **先转前 60 秒验证「音频顺序 = 文本顺序」这个假设，确认后再全量跑**，避免白跑 26 分钟。

### 对齐（文本 → 时间戳）

脚本 `listening/scripts/align_audio.py`：

1. 解析 docx → 结构化（passage / question / options / answer）。
2. 把每段文本和 whisper 词都**归一化成小写词序列**（去标点、去 speaker 标签、去「音频缺失」标记）。
3. `difflib.SequenceMatcher(None, ref_tokens, asr_tokens, autojunk=False)` 全局对齐。
4. 每个 ref 词映射到 asr 词 → 取 `min(start)` / `max(end)` 得到该段音频范围。

```python
sm = SequenceMatcher(None, ref_tokens, asr_tokens, autojunk=False)
ref_to_asr = [None] * len(ref_tokens)
for i, j, n in sm.get_matching_blocks():
    for k in range(n):
        ref_to_asr[i + k] = j + k
```

### 常见坑

| 问题 | 现象 | 解决 |
|---|---|---|
| whisper 词级时间戳错位 | 短句首词被拉到前一句结尾（幻影间隔 >10s） | 按「词间间隔 >3s 取大簇」丢弃离群词 |
| whisper 词带前导空格 | 对齐 `' where' != 'where'`，全匹配失败 | 归一化时 `.strip()` |
| 16kHz mp3 浏览器无声 | `Failed to load because no supported source` | 切片时 `-ar 44100` 重采样成标准 MPEG-1 |
| file:// 加载外部音频失败 | 相对路径 `clips/x.mp3` 找不到 | 音频 base64 内嵌进 HTML（单文件自包含） |
| OpenMP 冲突 | `libiomp5md.dll already initialized` | 设 `KMP_DUPLICATE_LIB_OK=TRUE` |

---

## 附：完整数据流

**造句题（OCR + LLM）**

```
raw-data/*.pdf
  → extract_images.py（pdfimages 拆图）
  → ocr_glm.py（GLM-OCR 本地识别，输出 glm_26.X.jsonl）
  → build_agent_input.py（拼成批次 JSON）
  → llm_order.py / agent（组词排序，输出 answers）
  → merge_final.py（合并 + 去标点 + 去重 + 打乱选项）
  → build.py（注入 template.html → quiz.html）
```

**听力（ASR + 对齐，`listening/` 目录）**

```
raw-data/*.m4a + 真题答案+文本.docx
  → ffmpeg（m4a → 16k 单声道 wav）
  → scripts/transcribe.py（faster-whisper large-v3，词级时间戳）
  → scripts/parse_transcript.py（docx → 题目/选项/答案 JSON）
  → scripts/align_audio.py（文本对齐时间戳 → manifest.json）
  → scripts/build_app.py（切片 mp3 + base64 内嵌 → 单文件 index.html）
```
