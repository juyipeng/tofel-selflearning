# 组句 · Build a Sentence

托福写作 Section 的第三个题型：给一句被打散的词，重组成语法正确的完整句子。

页面上每题分三块——提示句（上下文）、待填句（若干空位）、待选词（打散且可能混入干扰词）。

> 写作另外两个题型（Write an Email、Academic Discussion）在 [`../practice/`](../practice/)，
> 需要本地服务与 AI 打分；本模块是**自包含网页**，双击即可刷。

## 运行

```bash
python start.py sentence        # 在仓库根目录执行，自动打开浏览器
```

或直接打开 `quiz.html`。

## 数据管线

```
raw-data/*.pdf（原始题目 PDF）
  → extract_images.py   用 pdfimages 拆出每页图 → images/
  → ocr_glm.py          本地 GLM-OCR 逐图识别 → data/glm_26.X.jsonl
       （识别异常的被 reocr_abnormal.py 用更明确的「三部分」提示词重跑）
  → build_agent_input.py 每 40 题拼成一个 batch → data/agent_batches/
  → llm_order.py        DeepSeek 把打散的词重组成正确语序 → batch_XXX_result.json
  → merge_final.py      合并 OCR 与答案，去重、打乱选项 → data/questions_final.json
  → build.py            questions_final.json + template.html → quiz.html
```

OCR 底层调用已抽到仓库的 [`shared/ocr.py`](../../shared/ocr.py)。

## 文件

| 文件 | 作用 |
|---|---|
| `quiz.html` | **刷题页（产物）**，自包含，直接打开 |
| `template.html` | 刷题页模板（占位符 `__QUIZ_DATA__`） |
| `build.py` | `questions_final.json` + `template.html` → `quiz.html` |
| `extract_images.py` | 从 PDF 抽图（依赖 poppler 的 `pdfimages`） |
| `ocr_glm.py` | GLM-OCR 逐图识别（依赖本地 Ollama + `glm-ocr:q8_0`） |
| `reocr_abnormal.py` | 用更明确的提示词重跑识别异常的图 |
| `ocr_batch.py` | 阿里云 OCR 方案（早期尝试，现主要用本地 GLM-OCR；需 `aliyun_ocr_appcode`） |
| `rapidocr_group.py` | 用 RapidOCR 检测选项卡片分组 |
| `build_agent_input.py` / `build_input.py` | 拼 batch 输入 |
| `llm_order.py` | DeepSeek 批量排序（需 `deepseek_api_key`）；resume-safe |
| `merge_final.py` / `merge_data.py` | 合并 OCR 结果与答案 |
| `recompute_split.py` | 重算句子切分（修复用） |
| `agent_prompt.txt` | 交给 agent 批处理的提示词（与 `llm_order.py` 同一套规则） |
| `data/questions_final.json` | **结构化题库**（产物，入库） |
| `data/agent_batches/` | 中间批次输入与结果 |
| `raw-data/`、`images/` | 原始 PDF 与拆出的图（**不入库**） |

## 依赖

- **OCR**：本地 [Ollama](https://ollama.com) + `ollama pull glm-ocr:q8_0`；Python 侧要 `Pillow`
- **批量排序**：`langchain`、`langchain-openai`
- **拆图**：poppler（提供 `pdfimages`）

密钥从仓库根目录的 `config.json` 或环境变量读取，见根 [README](../../README.md#密钥配置)。
