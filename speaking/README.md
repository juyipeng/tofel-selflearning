# 口语刷题站（Listen and Repeat + Take an Interview）

7 月口语月刊的刷题工具，两种题型：

- **Listen and Repeat**（跟读）：19 个主题 × 7 句 = 133 句，放音频 → 显示文本 → 录音跟读 → 回放对比。
- **Take an Interview**（面试）：27 个单元 × 4 题 = 108 题，放音频 → 显示题目 → 录音回答 → **按 ETS 三维标准自动评分**。

## 文件

- `app/server.py` — 本地服务：静态托管 + `/api/score`（录音转写 faster-whisper + DeepSeek 评分）
- `app/practice.html` — 刷题界面（录音 / 回放 / 评分展示）
- `app/manifest.json` — 题目文本 + 音频路径
- `app/audio/` — 241 个 mp3
- `scripts/ocr_lr.py` — OCR 19 个 LR 主题页（GLM-OCR）
- `scripts/asr_int.py` — ASR 转写 108 个 INT 音频（faster-whisper）
- `scripts/build_manifest.py` — 合并 + 拷音频

## 配置

评分需要 DeepSeek key，从**仓库根目录的 `config.json`** 或环境变量 `DEEPSEEK_API_KEY` 读取
（环境变量优先）。首次使用：

```bash
cp config.example.json config.json    # 在仓库根目录执行
# 然后编辑 config.json 填入 key
```

`config.json` 已被 `.gitignore` 排除，不会提交。

## 运行（Windows）

**最简单的方式**：在仓库根目录执行

```bash
python start.py speaking          # 完整模式
python start.py speaking --lite   # 轻量模式
```

`start.py` 会自动按 `config.json` 里 `python.speaking` 指定的解释器启动。
**conda 环境：`pytorch`**（路径 `E:\conda_envs\pytorch`）—— 因为 `faster-whisper` 装在这个环境里。

### 手动启动：完整模式（跟读 + 面试评分）

- 双击 `app/start.bat`，或：
```bat
cd /d E:\code\personal_projects\TOEFL-learning\speaking\app
E:\conda_envs\pytorch\python.exe server.py
```

### 轻量模式（只跟读/录音回放，不加载模型、不评分、无需 GPU）

- 双击 `app/start_lite.bat`，或：
```bat
cd /d E:\code\personal_projects\TOEFL-learning\speaking\app
E:\conda_envs\pytorch\python.exe server.py --lite
```

启动后服务器会打印练习网址（默认 http://localhost:8766/practice.html），用浏览器打开即可。

> - 必须用 `localhost` 打开（不能 `file://`），否则浏览器禁用麦克风录音。
> - 完整模式首次启动要加载 faster-whisper 模型（约 1-2 分钟）；轻量模式秒开。
> - `KMP_DUPLICATE_LIB_OK` 已写在 server.py 里，无需手动设置。

## 麦克风输入源

录音前可在题目页面用「🎙 输入源」下拉框选择麦克风（解决系统默认输入不是想要的设备的问题）。选一次后本次会话记住，切换题目不丢失。

## 数据来源

- **LR 文字**：`新托福口语7月回顾.pdf` 是图片 PDF，用 `pdftoppm` 渲染整页再 GLM-OCR（注意：`pdfimages` 拆出的只有配图，不是题目文字）。
- **INT 文字**：PDF 里没有，用 faster-whisper 转写 108 个音频得到。
- **评分标准**：`interview-scoring.md`（ETS Take an Interview 三维标准），内嵌在 `server.py` 的 `SCORING_SYSTEM`。

## 评分流程

```
浏览器录音(MediaRecorder) → base64 → POST /api/score
  → faster-whisper 转写成文字
  → DeepSeek 按 Delivery/Language Use/Topic Development 三维打分
  → 返回转写文本 + 评分 + 提分建议
```
