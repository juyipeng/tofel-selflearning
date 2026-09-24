# GRE 免费刷题资源调研（2026-09）

> 目标：为「自建刷题网页」找可用的题源与词表。
> 每条都标注**免费程度**与**版权状态**——后者对公开仓库尤其关键。

---

## ★ 最大发现：ETS 官方免费真题 PDF（无需登录）

ETS 的「无障碍格式」页面把整套官方 practice test 以 **PDF 甚至 .docx** 公开挂出，
**无登录、无表单**：

**页面**：https://www.ets.org/gre/test-takers/general-test/prepare/test-prep-accessible-formats.html

**Practice Test 1**（已实测 HTTP 200 + application/pdf）：

| 文件 | 大小 |
|---|---|
| `gre-practice-test-1-quant-18-point.pdf` | 1.11 MB |
| `gre-practice-test-1-verbal-18-point.pdf` | 1.55 MB |
| `gre-practice-test-1-answers-18-point.pdf` | 答案 |
| `gre-practice-test-1-writing-18-point.pdf` + `-writing-responses-` + `-18-point-figures.pdf` + `-evaluating-performance-` | 写作与评分 |
| **`gre-practice-test-1-18-point-complete.zip`** | 5.35 MB（打包） |

**Practice Test 3** 同构（把 `1` 换成 `3`），打包 3.90 MB。

**★ 机器可读的 .docx 版（做题库最有用）**：
`gre-screen-reader-practice-test-1-quant.docx`（496 KB）、`-verbal.docx`（101 KB）、`-answer-key.docx`

> Practice Test 2 的 PDF **不存在**（逐个探测返回 404），只以 POWERPREP Online 机考形式提供。

**题目数量**（解压 PDF 数出来的，非估算）：
Verbal = Section 2「15 Questions」+ Section 3「20 Questions」= **35 题**；
Quant 同样 15+20 = **35 题**；AWA 1 篇。
→ 两套合计 **140 道真题**。

⚠️ **关键提醒**：这是**纸笔版格式**（35 题/项，2h15m），不是现行机考的 27 题/项（2h）。
题目是真题，但要复刻机考节奏需自己按 12+15 重新切分。

### 其他免费官方 PDF（全部实测可下载）

| 文件 | 链接 | 大小 |
|---|---|---|
| **Math Review**（约 100 页） | https://www.ets.org/content/dam/ets-org/pdfs/gre/gre-math-review.pdf | 2.74 MB |
| Math Review 打包（含分章 PDF 与 .doc 源文件） | `.../gre/gre-math-review-complete.zip` | 6.35 MB |
| Math Conventions | `.../gre/gre-math-conventions-18-point.pdf` | — |
| **Practice Book (Paper-delivered), 3rd ed** | https://www.ets.org/content/dam/ets-org/pdfs/gre/paper-delivered-test-practice-book.pdf | 5.17 MB |
| Quant 解题策略 | `.../gre/quantitative-reasoning-strategies.pdf` | 943 KB |
| Problem-solving strategies | `.../gre/gre-problem-solving-strategies-18-point.pdf` | 5.53 MB |
| 样题网页版（各题型带解析） | https://www.ets.org/gre/test-takers/general-test/prepare/content/verbal-reasoning.html 等 | 免费 |
| **Khan Academy 对照表** | https://www.ets.org/gre/test-takers/general-test/prepare/khan-prep-videos.html | 每个 Math Review topic → 具体 Khan 视频 |

> Practice Book 结构：1 篇 AWA + Verbal 15+20 + Quant 15+20，含
> Appendix A「Scored Sample Essay Responses and Rater Commentary」+ Appendix B「Interpretive Information」。© 2023。

### 免费模考

| 资源 | 链接 | 说明 |
|---|---|---|
| **POWERPREP 1**（不计时） | https://www.ets.org/gre/test-takers/general-test/prepare/powerprep.html | 全真长度，**不给 V/Q 分数**，给 AWA 范文；90 天有效，每套只能做一次 |
| **POWERPREP 2**（计时） | 同上 | 全真长度，有 V/Q 分数；**不给答案解析**（免费版最大缺陷） |
| Test Preview Tool | 账号内自动有 | 熟悉界面用，非完整题 |

付费对照：POWERPREP PLUS 三套各 $44.95；ScoreItNow 写作评分 $20；
Official Guide 4th ed $45；Official Verbal / Quant 练习册各 $25（各 150 题+解析）。

> ❌ **未能证实**：多个第三方博客称 ETS 有「免费 Official Question Bank，150+ 题，可按难度筛选」。
> 在 ETS 官网上**找不到**这个产品，只有付费书里的 150 题/本。当作未经证实。
>
> **Khan Academy 本身没有 GRE 课程**（官方 Help Center 明确说没有）。
> ETS 的做法是自建 topic→视频映射表，视频版权属 Khan Academy。

---

## 二、免费题库 / 网站

| 资源 | 链接 | 免费范围 | 需注册？ |
|---|---|---|---|
| **GRE Prep Club**（GMAT Club 系） | https://greprepclub.com/forum/ ／ https://gre.myprepclub.com/ | 题目+讨论+解析全免费；自称 Master Directory 有 16,000+ Quant、8,000+ Verbal | 浏览基本不用；计时器/收藏要注册 |
| **GregMat 免费模考** | https://www.gregmat.com/quizzes/quiz/full-practice-test-beta-1 （-2、-3） | **3 套全真模考**（自研题，非 ETS，作文不打分）+ 免费词表 | 需注册；题库 800+ 题属付费 |
| **Magoosh 免费模考** | https://magoosh.com/gre/gre-practice-test/ | section-adaptive，给估分+强弱项+解析 | 出分需账号 |
| Magoosh 免费 1000 词 flashcards | https://magoosh.com/gre/gre-vocabulary-flashcards/ | 1,000 词全免费，三级 + 间隔重复 | 存进度需账号 |
| **Manhattan Prep Starter Kit** | https://www.manhattanprep.com/gre/resources/ ／ .../free-gre-practice-test/ | 1 套 full-length 模考 + flashcards + App + 学习计划；另「Interact for GRE 试听 15 课」免费无信用卡 | 需注册 |
| Manhattan Prep App | iOS/Android「Manhattan Prep GRE Prep 2026」 | 免费含 1,000+ 题+详解、800+ drills、500 vocab cards | App 内账号 |
| Manhattan Review（**另一家公司**） | https://www.manhattanreview.com/gre-practice-questions/ （140 题免费） | 免费，另 500 题 Quant bank 需填表 | 填表 |
| Varsity Tutors | https://www.varsitytutors.com/gre-practice-tests | 免费诊断 + 分类 quiz（Quant 每套 10–12 题） | 官方称无需登录 |
| Achievable 免费 Quant 卷 | https://achievable.me/exams/gre/free-practice-exam/ | 免费 10 题带详解 | 否 |
| Vince Kotchian 免费资源 | https://vincekotchian.com/gre/free-gre-resources/ | study plan、error log 模板、math concept list | 否 |

---

## 三、可离线 / 可程序化获取

### GitHub 仓库（license 已用 GitHub API 逐个核实）

**✅ 有明确开源 license，可安全使用**

| 仓库 | ★ | License | 内容 |
|---|---|---|---|
| **bhargavyagnik/GRE-Flashcards** | 3 | **MIT** | **最实用的结构化词表**：`vocab.csv`(91 KB，多来源对照：Gregmat/Magoosh/Manhattan/PrepScholar/Powerscore/Vince/Greenlight 各列是否收录)、`data.json`(713 KB)、`wm.csv`(662 KB) |
| **skywind3000/ECDICT** | 8,322 | **MIT** | 77 万词条英汉词典数据库（CSV/SQLite/MySQL），自带 **GRE 考纲标签** + 音标 + 释义 + 词频 |
| LinXueyuanStdio/DictionaryData | 642 | **Apache-2.0** | 400+ 本单词书（含 GRE）+ 6 万词，JSON |
| hollamad/gregmat_vocab | 17 | **MIT** | `gregMatVocab.apkg` Anki 牌组 + 同义词 |
| ADGJSD/gre-recall | 20 | **MIT** | offline-first GRE 背词 App（含词库） |
| amitness/gre-cloze | 15 | MIT | GRE 完形填空（NLP 项目） |
| zyronon/TypeWords | 10,259 | GPL-3.0 | 打字背单词（⚠️ GPL 传染性，网页项目慎用） |

**⚠️ 无 LICENSE 文件 = 默认「保留所有权利」，法律上不能直接 copy 进自己项目**

| 仓库 | ★ | 内容 |
|---|---|---|
| Xatta-Trone/gre-words-collection | 30 | `word-list/` 下 15 个 CSV：`008 Magoosh-1000`、`006 Barrons-333`、`001 GregMat960`、`013 Manhattan-Prep-1000`、`combined.csv` 等。⚠️ 多为纯词表无释义 |
| kajweb/dict | 3,618 | GRE 7,199 词 JSON（含音标、同义、例句、真题），中文场景好 |
| mahavivo/english-wordlists | 2,509 | 去重词表合集（含 GRE、COCA） |
| fhb369/barron-s-333-words-and-their-mnemonics | 0 | `Barrons333_words.csv`、`Barrons800_words.csv`、助记 PDF |
| supersaiyanmode/GRE-Words-Magoosh | 17 | `Words.txt` + `process.dict` |
| **pycoder2000/GRE-Preparation-Material** | 33 | **含 Magoosh 官方 PDF 书籍——版权风险高，别 fork** |

### Anki 公开牌组

- **GregMat 词表牌组**：https://ankiweb.net/shared/info/962516846
  （来源帖 https://forums.ankiweb.net/t/gre-vocab-gregmat-supplemental/2558 ，另有补充牌组）
- AnkiWeb 搜索入口（自己筛）：https://ankiweb.net/shared/decks?search=GRE
- Manhattan 500 Advanced `.apkg`：https://file.ankichinas.cn/card/6a02834e7f710qSE
- **建议自建**：用上面 MIT 仓库的 CSV 直接生成，比下载来源不明的 .apkg 更干净

---

## 四、单词资源

| 词表 | 规模 | 免费获取途径 |
|---|---|---|
| Magoosh 1000 | 1,000 | 官网免费 flashcards；`Xatta-Trone/008 Magoosh-1000.csv` |
| Manhattan 500 Essential + 500 Advanced | 1,000 | Manhattan Prep App 内 500 flashcards；`013 Manhattan-Prep-1000-...csv` |
| Barron's 333 | 333 | `Xatta-Trone/006 Barrons-333.csv`；`fhb369` 的 CSV/PDF（含助记） |
| Barron's 800 | 800 | `fhb369/.../Barrons800_words.csv` |
| GregMat 词表 | 960–1,108 | `001 GregMat960.csv`；Anki 962516846 |
| GRE 3000+ / 5000 | 3,000 / 5,000 | `Xatta-Trone/009`、`/010` |
| **多来源去重对照** | — | **`bhargavyagnik/GRE-Flashcards` 的 `vocab.csv`（MIT，推荐）** |

---

## 五、版权状态 ★（上传 GitHub 必看）

### 🚫 ETS 版权，不能公开分发

包括上面所有很想打包的：
- 所有 `ets.org/content/dam/...` 的 Practice Test 1/3 PDF、screen-reader .docx、
  Practice Book、Math Review、Math Conventions。
  **PDF 内页明确印着** *"Unauthorized copying or reuse of any part of this page is illegal."* /
  *"Copyright © 2023 by ETS. All rights reserved."*
- POWERPREP 线上题目、ScoreItNow 范文、Official Guide / Verbal / Quant 练习册的题目与解析
- **ETS 曾对公开分发 POWERPREP 题目的站点发过下架通知，这是已知高风险区**

**建议做法**：PDF 只在本地解析 → 转成自己的数据结构 → 或在页面上放「导入 ETS PDF」按钮，
让用户自己下载。**ETS 内容不入库**。

### ⚠️ 其他商业机构版权

Magoosh / Manhattan / Barron's / Kaplan / Princeton Review / GregMat 的
**释义、例句、助记、题目**都是原创表达，受版权保护。

- **单词本身不受版权保护**（事实性列表）→ 纯 word list 风险较低
- **释义/例句/助记文本受影响** → `supersaiyanmode/Words.txt`、`kajweb/dict` 的例句、
  `fhb369` 的助记，都属灰色地带
- **无 LICENSE 的仓库默认「保留所有权利」**，不能直接 copy

### ✅ 可自由使用

- MIT：`bhargavyagnik/GRE-Flashcards`、`skywind3000/ECDICT`、`hollamad/gregmat_vocab`、
  `ADGJSD/gre-recall`、`amitness/gre-cloze`
- Apache-2.0：`LinXueyuanStdio/DictionaryData`
- GPL-3.0：`zyronon/TypeWords`（传染性，慎用）
- 用 MIT 时记得保留 copyright notice

### 🟢 无版权之虞

- 单词、词性、音标（事实数据）
- 自制的题目解析
- ETS 官网公开的题**型**描述（facts）
- varsitytutors / greprepclub 的题目 —— 但**这些站点的 ToS 通常禁止爬取和再分发**，
  即使版权上可能不受保护，爬取仍受 ToS 限制

---

## 六、对「自建刷题网页」最实用的 5 个来源

1. **ETS 官方 Practice Test 1 & 3 PDF + screen-reader .docx**
   → 唯一能免费拿到的**真题**，`.docx` 版可直接 regex 解析成结构化题目。
   Verbal 35 + Quant 35，两套共 **140 道**。
   做法：**本地解析、不入 public repo**，或做「导入 ETS PDF」入口。

2. **GRE Prep Club 论坛** https://gre.myprepclub.com/forum/
   → 规模最大的免费题库（自称 16k Quant + 8k Verbal）。
   注意 ToS，**建议只做链接跳转而非全文搬运**。

3. **`bhargavyagnik/GRE-Flashcards`（MIT）**
   → 唯一一个 MIT + 多来源对照 + 有 CSV/JSON 的词表数据源。
   可直接进 repo，撑起「这个词出现在哪些词书里」的功能。

4. **`skywind3000/ECDICT`（MIT）**
   → 8.3k star 的英汉词典数据库，自带 GRE 考纲标签 + 音标 + 释义 + 词频。
   做点词查义、自动生成 flashcard 背面，比抓商业词表干净得多。

5. **GregMat 免费 3 套模考 + Magoosh 免费 1000 词**
   https://www.gregmat.com/quizzes/quiz/full-practice-test-beta-1
   ／ https://magoosh.com/gre/gre-vocabulary-flashcards/

### 建议的数据分层

```
真题层   ETS PDF          → 本地导入 / 不入库
自造题层 自己写解析        → 完全干净，可公开
词表层   MIT 仓库 + ECDICT → 可公开
链接层   指向 greprepclub / Magoosh → 只跳转不搬运
```

这样 GitHub 公开最安全。
