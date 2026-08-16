# OPC 12 · DECISIONS（关键决策记录）

> 恒哥在 2026-08-15 14:17 创建 OPC 12 时只有 Kickstarter + IT之家 两个源（旧版 today.json 5 条样本）。
> 2026-08-16 11:18 起 **重新设计**：5 源、每天 10 条、保留"主标题+概要描述"展示。
> 本文件记录所有架构/源替换/抓取方式的决策。

---

## DEC-001 · 5 源 × 2 条 = 10 条/天

**时间**: 2026-08-16 11:18
**决策者**: 恒哥
**内容**: 总共 5 个数据源，每天 10 条（每源 2 条）

**理由**: 5 源覆盖广，每源 2 条避免单源霸屏。10 条是单卡片能塞下的最大信息量（3:4 比例限制）。

---

## DEC-002 · 虎嗅 → 少数派（替换）

**时间**: 2026-08-16 11:25（探测后决定）
**决策者**: 小蔚拍板，待恒哥 review
**内容**: 恒哥原指定源"虎嗅 huxiu.com" 替换为 "少数派 sspai.com"

**理由**:
- 虎嗅全站被阿里云 WAF 滑块验证挡死
- Playwright + stealth（`--disable-blink-features=AutomationControlled` + 中文 locale）也破不了
- 虎嗅的 RSS endpoint（`/rss/`、`/feed`、`/rss/0.xml`）都返回 WAF 验证页面
- 虎嗅 article-api.huxiu.com 返回 200 但所有路径 404（找不到正确 endpoint）
- 少数派（sspai.com）有公开 JSON API：`https://sspai.com/api/v1/articles?offset=0&limit=10`
  - 直接返回 title + summary（**已含概要**，不用抓详情页）
  - JSON 干净，字段齐全（id / title / summary / banner / released_at）
  - 调性：科技生活方式 / 工具向，跟虎嗅接近

**回滚方法**: 改 SOURCES 配置，移除 sspai，加 huxiu 即可（huxiu 配置需要新写 Playwright stealth 脚本，**当前未实现**）

---

## DEC-003 · 36氪 → Solidot（替换）

**时间**: 2026-08-16 11:35（探测后决定）
**决策者**: 小蔚拍板，待恒哥 review
**内容**: 恒哥原指定源"36氪 36kr.com" 替换为 "Solidot solidot.org"

**理由**:
- 36kr 在新加坡 IP 被 Cloudflare 风控
- Playwright headless 抓首页：HTML 只 3690 字节、title 为空（= 没渲染内容）
- 之前 probe 测试时是 OK 的（HTML 206KB，131 个 /p/ 链接），说明 IP 段被风控 + 时效
- 36kr 的 `/feed` 等所有 RSS 路径都被同一个 Cloudflare 拦死
- Solidot RSS `https://www.solidot.org/index.rss` 100% 稳定（21KB RSS，标准 RSS 2.0）
- 调性：Solidot 是科技深度新闻（创客/IT），跟 36kr 创投类接近

**回滚方法**: 改 SOURCES 配置，移除 solidot，加 36kr（36kr Playwright 配置需要新写 + 多次 selector fallback，可能仍不稳）

**备注**: 如果恒哥能接受"36kr 偶尔抓不到（少 2 条）"，可以加 36kr 当 **fallback**（抓不到时降级）

---

## DEC-004 · 抓取策略：RSS > JSON API > Playwright

**时间**: 2026-08-16 11:25
**决策者**: 小蔚
**内容**: 5 源按以下优先级抓取，稳定性递减：

| 优先级 | 类型 | 源 | 优点 | 缺点 |
|---|---|---|---|---|
| 1 | RSS | 爱范儿 / Solidot / IT之家 | 100% 稳定、最快 | 部分源 RSS 不更新 |
| 2 | JSON API | 少数派 | 稳定、字段完整 | 路径可能要追前端 JS |
| 3 | Playwright 首页 + 详情 | 果壳 | RSS 不可用时的兜底 | 慢 + 不稳定（首页可能 JS 渲染慢） |

**理由**:
- RSS 最稳优先（无 JS 渲染、无风控）
- JSON API 次之（结构化 + 不渲染）
- Playwright 兜底（最慢 + 最不稳，但能拿到所有公开页面）

**性能影响**: 每天 fetch 全跑约 60-90s（果壳 Playwright 占大头，约 30-40s）

---

## DEC-005 · 概要描述抓取：RSS description > JSON summary > meta description > first `<p>`

**时间**: 2026-08-16 11:30
**决策者**: 小蔚
**内容**: 对每个 item，按以下优先级获取 subtitle：

1. RSS `<description>`（爱范儿 / Solidot / IT之家）
2. JSON `summary` 字段（少数派）
3. 详情页 `meta[name="description"]`（果壳 / 36kr）
4. 详情页第一个 `<p>` 元素（兜底）

**理由**:
- RSS 和 JSON 自带 description 最省事
- 果壳 / 36kr 没 RSS 只能抓详情页
- meta description 失败时用 first `<p>` 兜底（避免空 subtitle）

**subtitle 长度限制**: 160 字符（多余会被截断）

---

## DEC-006 · 卡片配色按源区分（不用 source ID）

**时间**: 2026-08-16 11:35
**决策者**: 小蔚
**内容**: 每个源在卡片上有专属色，标签 `background: transparent; border: <color>`：

| 源 | 色 | 含义 |
|---|---|---|
| 果壳 | 🟢 #83C176 | 自然/科普 |
| 爱范儿 | 🔴 #F25C54 | 热情/数字 |
| Solidot | 🔵 #1F6FEB | 专业/深度 |
| 少数派 | 🟠 #D9472A | 创造/橙调 |
| IT之家 | 🔵 #2C7BE5 | 数码/科技蓝 |

**理由**: 视觉上一眼能区分 5 源 + 标签字号统一（14px mono）

---

## DEC-007 · 卡片尺寸 3:4 (1140×1620)

**时间**: 2026-08-16 11:35
**决策者**: 小蔚
**内容**: 卡片输出 1140×1620px（Playwright 截图 device_scale_factor=2 → 实际 2280×3240px）

**理由**:
- 小红书标准比例 3:4
- 10 条内容需要 1620 高度（原 1520 不够 10 条）
- device_scale_factor=2 让文字在 retina 屏清晰

---

## 待定决策

- **DEC-008（✅ 已选 GitHub Actions，11:41）** · cron 架构选择（GitHub Actions vs 本地 launchd）
- **DEC-009（✅ 已改名字，11:41）** · 目录名已改：`12_科技聚合_科技资讯5源`
- **DEC-002/003（✅ 已接受，11:41）** · 虎嗅→少数派 / 36kr→Solidot 两个替换
- **DEC-010（待）** · 缩略图是否要（fetch 抓 banner → 本地，render 优先用 image_path）
- **DEC-011（待）** · 卡片是否要导公众号 / 老蔚社圈
## DEC-013 · 3 源替换为 AI 资讯（2026-08-16 15:12 拍板）

**背景**：原 5 源中只有 Solidot 偶尔有 AI 资讯，AI 浓度太低。恒哥要求换源提 AI 浓度到 60%。

**决策**：

| 原源 | 新源 | 类型 | 抓取方式 |
|------|------|------|----------|
| 爱范儿 ifanr | **量子位 qbitai.com** | 中文 AI 第1 | RSS `https://www.qbitai.com/feed` |
| 少数派 sspai | **The Decoder the-decoder.com** | 英文 AI 第1 | RSS `https://the-decoder.com/feed/` |
| IT之家 ithome | **Hacker News** | 英文科技风向 | RSS `https://news.ycombinator.com/rss` |

**保留**：果壳（科技杂）+ Solidot（科技深度）

**新 5 源配置**：
- 果壳（Playwright） — 保留
- 量子位（RSS） 🆕
- Solidot（RSS） — 保留
- The Decoder（RSS） 🆕
- Hacker News（RSS） 🆕 — 描述清洗（HN 描述只有 "Comments" 链接）

**AI 浓度**：从 0~20% → 60%（3/5 源 100% AI）

**技术细节**：
- 新增 `fetch_rss_hn()`：识别 HN 的 description 仅为 "Comments" 链接，清洗后留空
- `fetch_rss()` 通用化：去掉原"爱范儿 / IT之家"专属注释，所有 RSS 源通用

## DEC-014 · 多尺寸 + emoji + 头条智能主推（2026-08-16 16:12 P1）

### P1-B · 头条图智能挑（DEC-014）
头条图原来固定取 `items[0]`（可能是果壳做牛排），现在按 **源 AI 浓度优先级**挑：

```
量子位(5) > The Decoder(4) > Solidot(3) > HN(2) > 果壳(1)
```

效果：现在头条图 100% 推 AI 资讯（量子位 / The Decoder 优先）。

### P1-C · 源 emoji 图标
| 源 | emoji |
|---|---|
| 果壳 | 🌿 |
| 量子位 | 🧠 |
| Solidot | 🛰️ |
| The Decoder | 🤖 |
| Hacker News | 🔥 |

应用：所有尺寸的 `placeholder` / `src label` 都加 emoji，视觉一眼识别源。

### P1-A · HN/英文源 OG description 自动补抓
HN RSS description 只含 "Comments" 链接（无法从 RSS 拿概要）。新增 `enrich_og_description()`：
- 抓完全部 RSS 后，对 `subtitle` 为空的条目用 Playwright 抓详情页 `og:description`
- 找不到 OG 的（404 / 老链接）就留空，不影响卡片

## DEC-017 · 翻译服务选 C（Google Translate 免费）· 实际用 MyMemory（2026-08-16 16:44）

**背景**：恒哥要求英文资讯翻译成中文。先选了 DeepL（需 API key），恒哥改选 **C. 接 Google Translate 免费接口**。

**实际执行**：
1. Google Translate 隐藏 API（`translate.googleapis.com/translate_a/single`）—— **已被官方封死**，返回 `{"src":""}` 空响应
2. 降级到 **MyMemory translated.net**（`api.mymemory.translated.net/get`）—— ✅ 工作正常
   - 免费 5000 字符/天/IP（足够 OPC12 用：~2000 字符/天）
   - 无需 API key
   - 稳定可商用

**翻译效果**（2026-08-16 7 段全成功）：
- Anthropic's bio-weapons filter → Anthropic的生物武器过滤器关闭了近一年，暴露了1.33亿个请求 ✅
- Optima tackles AI benchmarking → Optima通过让用户根据自己的数据测试模型来解决人工智能基准测试的最大缺陷 ✅
- LLM → 法学硕士 ⚠️ （字面翻译"法学硕士"，实际应为"大语言模型"，P2 待优化）
- Asus Bike Booster → 华硕自行车助推器 ✅

**实施**：
- `scripts/03_translate.py` 改用 MyMemory
- `.github/workflows/daily.yml` 去掉 DEEPL_API_KEY 依赖（MyMemory 不用 key）
- fetch 流程：00_fetch.py → 03_translate.py → commit data → render 触发

**P2 待优化**：
- LLM 术语本地化词典（避免 MyMemory 字面翻译）
- 翻译质量监控（标题长度异常 / 中英混杂检测）

## DEC-017 P2 · 术语词典修正 LLM 误译（2026-08-16 16:49）

**问题**：MyMemory 翻译 "LLM" 时字面返回 "法学硕士"（当成 Master of Laws）。

**修法**：占位符策略 + 翻译后字符串替换：
1. **翻译前预处理**：`LLM` → `__LLM__`（占位符）
   - MyMemory 看到 `__LLM__` 不会翻译（即使翻也会保留 `__` 形式）
2. **翻译后还原**：`__LLM__` → "大语言模型"
   - 同时容忍 MyMemory 加空格（`__ LLM __`）
3. **已知错误修正表**：
   - 法学硕士/理学硕士 → 大语言模型
   - 人性人 → Anthropic
   - Optima平台平台 → Optima
   - 人工分析推出了Optima → Artificial Analysis 推出了Optima

**生效后验证**：HN 第 2 条标题从"当法学硕士..." → "当大语言模型从未看到五年级以上的材料时会发生什么？" ✅

## DEC-018 · 去掉果壳 + 4 源配额 + 卡片紧凑化（2026-08-16 16:54）

恒哥 16:54 拍板两件事：
1. 去掉果壳（综合科普源，AI 含量最低）
2. 紧凑化卡片（之前下半部空白太多）

### 实施

**SOURCES 改成 4 源**（`scripts/00_fetch.py`）：
```
量子位  3 条/天
The Decoder  3 条/天
Solidot  2 条/天
Hacker News  2 条/天
─── 合计 10 条/天
```
新增 `SOURCE_QUOTAS` 字典，让 fetch 按源配额裁剪（之前是统一 `PER_SOURCE=2`）。

**AI 浓度**：果壳是 5 源里 AI 含量最低的（综合科普），去掉后 4 源里 6 条都是 AI（量子位 3 + The Decoder 3），剩 4 条 Solidot/HN 是部分 AI 或随机。AI 浓度从 60% → **80~90%**。

**紧凑化 CSS**（`scripts/02_render_multi.py`）：
- wrap padding: `H*0.04 / W*0.05 / H*0.03` → `H*0.025 / W*0.035 / H*0.02`（-40%）
- title margin-top: 12 → 8
- subtitle margin-top: 8 → 4
- divider margin-top: 14 → 8 + width 50 → 40
- list margin-top: 14 → 8
- row padding: 8 10 → 7 10
- row gap: 10 → 6（vertical）/ 8 → 5（horizontal）
- 16:9 cell 加上 subtitle-row（之前只显示标题）+ 用 `-webkit-line-clamp` 限 3 行标题 + 8 行概要
- footer margin-top: auto → 6

**小 bug**：之前加的 `min-height` 导致朋友圈 1:1 渲染崩溃（playwright 卡死），改为 `flex:1` + `justify-content:space-between` 让 row 紧贴 footer。

### 最终卡片（2026-08-16 21:18）

| 文件 | 尺寸 | 大小 |
|---|---|---|
| `20260816_2118_xiaohongshu_card1.png` | 3:4 (1140×1620) | 956 KB |
| `20260816_2118_friend_card1.png` | 1:1 (1080×1080) | 898 KB |
| `20260816_2118_wechat_16x9_card1.png` | 16:9 (1280×720) | 640 KB |
| `20260816_2118_wechat_16x9_card2.png` | 16:9 (1280×720) | 629 KB |
| `20260816_2118_wechat_top_card1.png` | 2.35:1 (900×383) | 330 KB |
