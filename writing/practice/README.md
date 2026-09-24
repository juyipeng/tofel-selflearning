# 写作刷题站（Email + Academic Discussion）

在 `writing/` 下新造的写作刷题工具，专注 **Write an Email** 和 **Academic Discussion** 两个题型（组句 Build a Sentence 忽略，用 `make-a-sentence/` 那套）。

## 文件

- `extract.py` — 拆题脚本：解压真题 zip → 渲染 PDF 页 → GLM-OCR → 定位并解析 Email/Discussion 题目 → `data/questions.json`
- `data/questions.json` — 提取出的题目（28 套：10套精选 + 7月7套 + 8月11套）
- `data/raw/*.txt` — 每套的原始 OCR 文本（校对用）
- `server.py` — 本地服务：静态托管本目录 + `/grade` 代理转发 DeepSeek（打分 + 导师对话共用）
- `practice.html` — 刷题界面

## 运行

```bash
cd writing/practice
python server.py            # 默认 http://localhost:8765
# 浏览器打开 http://localhost:8765/practice.html
```

## 功能

1. **选题 + 计时**：Email 7 分钟 / Discussion 10 分钟，倒计时**不硬断**——到点变红继续走表，并**自动保存「限时版本」**（那一刻的作答）。
2. **AI 打分**：把「题目 + 作答 + 评分提示词」发 DeepSeek，返回三维度打分 + 提分建议；**超时则限时版和最终版各打一次分**。
3. **探讨改进**：打分后点「💬 探讨改进」，AI 扮演写作导师，把题目/作答/批改结果放进上下文，可多轮问答、讨论如何改进。
4. **重新做题 / 修改旧答**：进题后自动载入上次作答可继续改，点「↺ 重新做题」清空重写。
5. **做题记录 + 统计**：每次提交记录得分 + 用时，数据统计页展示平均分/平均用时/超时次数 + 趋势图 + 明细表。
6. **保存 / 加载 / 重置**：记录自动存本地浏览器；顶栏「保存」导出 JSON、「加载」导入、「重置」清空。

## 拆题（补充更多真题时）

```bash
# 先确保 Ollama 在跑，且已拉取 glm-ocr:q8_0
python extract.py            # 默认拆「写作精选套题练习10套.zip」
python extract.py --zip ../7月真题.zip
python extract.py --zip ../8月真题.zip
```

要点：
- 打分/导师用模型在 `practice.html` 写死为 `deepseek-v4-flash`，可在 `server.py` 的 `DEFAULT_MODEL` / key 处改。
- 评分提示词内嵌在 `practice.html`，源自「写作答题卡」。
- 7月真题是竖版、8月/10套是横版；竖版超高页 GLM-OCR 会漏底部，`extract.py` 已做「上下切块 OCR」兜底。
- 部分套题（约 5 套）的 Discussion 是「教授摆出正反两面 + 提问」型，本身没有学生发言，属正常变体。
