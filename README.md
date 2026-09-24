# TOEFL-learning

托福自学/复习的刷题工具集。把练习材料变成可以随时打开就刷的网页，覆盖词汇、阅读、听力、口语、写作五块。

每个模块都是一条独立的管线：**原始材料 → Python 抽取 → 结构化 JSON → 注入 HTML 模板 → 自包含刷题页**。产物网页大多不依赖服务端，双击就能用。

---

## 模块总览

| 模块 | 内容 | 形态 | 启动 |
|---|---|---|---|
| **词汇** [flashcards.html](flashcards.html) | 1012 词，音标 / 释义 / 例句 / 短语，支持背诵与标记 | 自包含网页 | `python start.py flashcards` |
| **阅读** [reading/](reading/) | 填词题 + 阅读选择 + 句子插入，做完即对答案 | 自包含网页 | `python start.py reading` |
| **听力** [listening/](listening/) | 音频内嵌，逐题播放 + 作答 | 自包含网页 | `python start.py listening` |
| **口语** [speaking/](speaking/) | Listen and Repeat（跟读）+ Take an Interview（录音 + AI 按 ETS 三维标准评分） | 需本地服务 | `python start.py speaking` |
| **写作** [writing/](writing/) | Write an Email + Academic Discussion，AI 三维打分 + 探讨改进 + 素材库 | 需本地服务 | `python start.py writing` |
| **组句** [make-a-sentence/](make-a-sentence/) | 打散的词重组成正确句子 | 自包含网页 | `python start.py sentence` |

`python start.py` 不带参数会列出以上全部。

---

## 快速开始

```bash
git clone <本仓库>
cd TOEFL-learning

# 配置密钥（只有口语/写作的 AI 评分用得到）
cp config.example.json config.json
# 编辑 config.json，填入你的 DeepSeek key

# 直接刷静态模块（不需要任何 Python 依赖）
python start.py reading

# 起服务类模块
python start.py writing
python start.py speaking          # 需要 faster-whisper，见下文
```

---

## 环境要求

不同模块依赖不同，**不需要全部装**。用哪个装哪个：

| 用途 | 环境 | 依赖 |
|---|---|---|
| 起 `writing` 服务 | 任意 Python 3 | 仅标准库 |
| 起 `speaking` 服务、听力转写 | 装了 faster-whisper 的环境 | `faster-whisper`（带 CUDA 更好） |
| `make-a-sentence/llm_order.py` 批量组句 | 任意 Python 3 | `langchain`、`langchain-openai` |
| 所有 OCR 脚本 | 任意 Python 3 | `Pillow` + 本地 [Ollama](https://ollama.com) |
| 视频/音频切分（重建听力模块时） | 系统 PATH | `ffmpeg` |

```bash
# OCR 模型（本地跑，无配额限制）
ollama pull glm-ocr:q8_0      # 约 1.6 GB
```

口语模块需要在装有 `faster-whisper` 的解释器下运行。在 `config.json` 里指定：

```json
"python": { "speaking": "E:/conda_envs/pytorch/python.exe" }
```

留空则用当前解释器。轻量模式（不加载模型、只跟读和录音回放）不需要 GPU：

```bash
python start.py speaking --lite
```

---

## 密钥配置

只有**口语评分**和**写作打分**需要 API key。取值优先级：**环境变量 > `config.json`**。

```bash
# 方式一：环境变量
export DEEPSEEK_API_KEY=sk-xxx
export ALIYUN_OCR_APPCODE=xxx

# 方式二：配置文件（推荐，见 config.example.json）
cp config.example.json config.json
```

`config.json` 已在 `.gitignore` 中，不会被提交。`config.example.json` 是可提交的模板。

| 配置项 | 用途 | 谁在用 |
|---|---|---|
| `deepseek_api_key` | 口语/写作 AI 评分、批量组句 | `speaking/app/server.py`、`writing/practice/server.py`、`make-a-sentence/llm_order.py` |
| `aliyun_ocr_appcode` | 阿里云 OCR（组句题早期方案，现主要用本地 GLM-OCR） | `make-a-sentence/ocr_batch.py` |

---

## 各模块说明

### 词汇 flashcards.html

从 [vocab_data.json](vocab_data.json) + [template.html](template.html) 生成：

```bash
python build.py      # -> flashcards.html
```

### 阅读 reading/

数据管线（从原始 docx/PDF 到刷题页）：

```
extract_images.py  → extract_images.py（从 docx 的 word/media/ 抽原图）
                   → ocr_read.py（本地 GLM-OCR 识别）
                   → parse_answer_key.py（解析答案表）
                   → parse.py（合成结构化 questions.json）
                   → build.py（注入模板 → quiz.html）
```

题型与经验细节见 [reading/](reading/) 与 [OCR_ASR_LLM_GUIDE.md](OCR_ASR_LLM_GUIDE.md)。

### 听力 listening/

关键思路是**不做听写、做强制对齐**：材料里已有逐字稿，所以只需要 word 级时间戳，用 `difflib` 把已知文本映射到秒，得到每题的音频区间。

```
transcribe.py（faster-whisper 词级时间戳）
  → parse_transcript.py（解析逐字稿 → 题目/选项/答案）
  → align_audio.py（文本对齐时间戳 → manifest.json）
  → build_app.py（切片 mp3 + base64 内嵌 → 单文件 index.html）
```

### 口语 speaking/

```bash
python start.py speaking          # 完整模式，含评分
python start.py speaking --lite   # 轻量模式：不加载模型、无需 GPU
```

> 必须用 `localhost` 打开（不能用 `file://`），否则浏览器禁用麦克风。
> 页面内可用「🎙 输入源」切换麦克风设备。

评分流程：浏览器录音 → base64 → `/api/score` → faster-whisper 转写 → DeepSeek 按 Delivery / Language Use / Topic Development 三维打分。

### 写作 writing/

```bash
python start.py writing
# 刷题站   http://127.0.0.1:8765/practice.html
# 素材库   http://127.0.0.1:8765/materials.html
```

计时倒计时到点不硬断（变红继续走表并另存限时版）；提交后 AI 三维打分 + 提分建议 + 可多轮「探讨改进」。素材库支持 AI 找素材、逐句背诵默写。

### 组句 make-a-sentence/

拆图 → OCR → LLM 把打散的词重组成正确语序 → 合成刷题页。见 [make-a-sentence/](make-a-sentence/)。

---

## 目录结构

```
TOEFL-learning/
├── start.py                 统一入口
├── config.example.json      配置模板（复制成 config.json）
├── shared/                  跨模块共用：config.py（密钥/端口）、ocr.py（GLM-OCR 调用）
├── flashcards.html          词汇刷题页（产物）
├── vocab_data.json          词汇数据
├── build.py, template.html  词汇生成器与模板
├── reading/                 阅读模块
├── listening/               听力模块
├── speaking/                口语模块
├── writing/                 写作模块
├── make-a-sentence/         组句模块
└── OCR_ASR_LLM_GUIDE.md     OCR / ASR / 批量 LLM 的踩坑记录
```

各模块目录内通常有：`raw-data/`（原始材料，不入库）、`images/`、`data/`（中间与结构化数据）、`scripts/`、以及生成好的网页产物。

---

## 别处也可能有用

[OCR_ASR_LLM_GUIDE.md](OCR_ASR_LLM_GUIDE.md) 记录了这套流程里踩过的坑，与托福本身无关，做类似事情时可以复用：

- **本地 OCR**（Ollama + GLM-OCR）：为什么小模型要用简单提示词、超宽图为什么识别失败
- **批量 LLM 结构化输出**：用脚本一次处理上千条，比派大量 agent 更快
- **音频强制对齐**：有逐字稿时怎么把连续音频切成逐题片段，以及 whisper 词级时间戳的错位处理

---

## 说明

- 本仓库代码以 MIT 协议开源，见 [LICENSE](LICENSE)。
- 仓库内的练习题目数据为个人学习用途整理，**不声明任何来源**；如你是相关权利人并认为此处内容不妥，请提 issue，我会移除。
- 口语/写作的 AI 评分由 DeepSeek 提供，需要你自己的 API key。
