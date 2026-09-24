# writing · 托福写作练习

本目录是托福写作练习的整套工具，包含刷题站和素材库两个网页，共用一个本地服务。

## 目录结构

```
writing/
├── 7月真题.zip              真题 PDF（7 套）
├── 8月真题.zip              真题 PDF（11 套，按日期分子目录）
├── 写作精选套题练习10套.zip   精选写作练习（10 套）
├── 【套题专用】写作答题卡.docx   答题卡模板（含 AI 评分提示词）
└── practice/                服务与网页（见下）
    ├── server.py            本地服务（刷题 + 素材共用一个服务）
    ├── practice.html        写作刷题站
    ├── materials.html       素材库（积累 / 总结 / 背诵）
    ├── extract.py           拆题脚本（从真题 zip 提取 Email + Discussion 题目）
    ├── data/questions.json  已提取的 28 套题目
    ├── data/records.json    做题记录（服务端自动保存）
    └── data/materials.json  素材库（服务端自动保存）
```

## 配置

打分和 AI 互动需要 DeepSeek key，从**仓库根目录的 `config.json`** 或环境变量 `DEEPSEEK_API_KEY` 读取
（环境变量优先）。首次使用：

```bash
cp config.example.json config.json    # 在仓库根目录执行
# 然后编辑 config.json 填入 key
```

`config.json` 已被 `.gitignore` 排除，不会提交。

## 启动服务

**最简单的方式**：在仓库根目录执行 `python start.py writing`。

**Python 环境**：直接用系统默认的 `python`（Anaconda base，Python 3.12）即可，**无需激活任何 conda 环境**。

- `server.py` 只用 Python 标准库（`http.server` / `urllib`），任何 Python 3 都能跑。
- `extract.py`（拆题）需要 Pillow（`PIL`），base 环境已自带（PIL 10.x）。

```bash
cd writing/practice
python server.py            # 默认 http://localhost:8765
```

启动后会打印两个链接：

```
写作刷题站：   http://127.0.0.1:8765/practice.html
素材库：       http://127.0.0.1:8765/materials.html
```

按 `Ctrl+C` 退出。若端口被占，可用 `python server.py --port 9000` 换端口。

> 服务需要能联网访问 DeepSeek（打分、AI 互动、自动总结都用它）。key 从仓库根目录的 `config.json` 读取，模型名在 `server.py` 顶部改动。

## 一、写作刷题站（practice.html）

练习 **Write an Email**（7 分钟）和 **Academic Discussion**（10 分钟）：

- **计时**：倒计时不硬断，到点变红继续走表，并自动保存「限时版本」。
- **打分**：提交后把「题目 + 作答 + 评分提示词」发给 DeepSeek，返回三维度打分 + 提分建议；超时则限时版和最终版各打一次。
- **探讨改进**：打分后点「💬 探讨改进」，AI 扮演写作导师，可多轮问答讨论怎么改。
- **重新做题 / 修改旧答**：进题自动载入上次作答可继续改，顶栏「↺ 重新做题」清空重写。
- **记录与统计**：每次提交记得分 + 用时，统计页有平均分/平均用时/超时次数 + 趋势图 + 明细表。
- **保存 / 加载 / 重置**：记录自动存服务端（`data/records.json`），顶栏「保存」写回、「加载」重读、「重置」清空。

## 二、素材库（materials.html）

素材 = 支撑观点的**具体例子**（一本书 / 一个活动 / 一项研究 / 一个事实 / 一个人物），不是观点本身。

- **💬 AI 互动**：和 AI 讨论一个 topic，确定例子素材，一键保存。
- **✨ 自动找素材**：读取题库主题关键词（不给你看原题、不给分析过程），归纳出能覆盖多题目的通用例子素材。点「讨论/修改」可进编辑器，和 AI 一起打磨，改好再保存。
- **📝 背诵默写**：逐句盲写，凭记忆打出英文，逐词比对给准确率（≥95% 标记已掌握）。
- **导出 md**：一键导出和 `bank of materials/*.md` 同格式的文件。

素材库和掌握进度自动保存：素材存服务端 `data/materials.json`；掌握进度存浏览器 localStorage。

## 三、拆题（补充新真题时）

把新的真题 zip 放进 `writing/`，然后：

```bash
cd writing/practice
# 先确保 Ollama 在跑，且已拉取 glm-ocr:q8_0
python extract.py --zip ../<新真题>.zip
```

拆题脚本会自动解压（处理中文文件名）、渲染 PDF 页、用本地 GLM-OCR 识别、定位并解析 Email/Discussion 题目，合并进 `data/questions.json`。

## 常见问题

- **打分报 `DeepSeek 调用失败`（SSL/连接拒绝）**：网络偶发断连，已内置 5 次重试；若仍失败说明那一刻网络到 DeepSeek 不通，换网络/过几分钟再试。
- **改了 server.py 不生效**：需重启服务（`Ctrl+C` 后重新 `python server.py`）。
