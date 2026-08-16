# OPC 12 · DONE（已完成）

> 倒序时间，最新的在上面

---

## 2026-08-16 11:37 · 全链路跑通 ✅

- `00_fetch.py` → `data/2026-08-16.json`（10 条）
- `01_render_card.py` → `~/Documents/code poj/photo/OPC12_科技聚合/20260816_1137_科技聚合.png`（1.2MB，3:4 卡片）
- 5 源全绿：果壳 ✅ / 爱范儿 ✅ / Solidot ✅ / 少数派 ✅ / IT之家 ✅

## 2026-08-16 11:35 · 5 源配置最终版

- 虎嗅→少数派（DEC-002）
- 36kr→Solidot（DEC-003）
- 5 源混合抓取策略落地（DEC-004）：RSS > JSON API > Playwright

## 2026-08-16 11:30 · 抓取脚本 `00_fetch.py` 写好

- 5 源配置 + 3 种抓取器（fetch_rss / fetch_json_api / fetch_playwright_list）
- 失败容错：单源失败不影响整体（try/except 包每源）
- 输出结构：date / total / sources / items 四字段
- 概要 description 抓取 DEC-005：RSS > JSON > meta > first p

## 2026-08-16 11:25 · 探查 5 源可达性 + 决定替换 2 源

- ✅ 爱范儿 RSS（724KB，含 description）
- ✅ IT之家 RSS（215KB，含 description）
- ❌ 虎嗅 WAF 验证页挡死 → 换 少数派
- ❌ 36kr Cloudflare 风控 → 换 Solidot
- ✅ Solidot RSS（21KB）
- ✅ 少数派 JSON API（58KB）
- ✅ 果壳 Playwright 首页可解析（47 个 article 链接）

## 2026-08-16 11:22 · 恒哥下达新指令

> "去掉 https://www.kickstarter.com/?lang=zh，增加 guokr.com / ifanr.com / 36kr.com / huxiu.com / ithome.com，每天十条，展示主标题和概要描述"

- 解读：5 源 = 果壳/爱范儿/36氪/虎嗅/IT之家
- 每天 10 条（之前 5 条）
- 卡片展示字段：title + subtitle（概要）

## 2026-08-15 14:17 · OPC 12 立项（初版）

- 目录创建：`12_科技聚合_科技资讯5源`
- `data/today.json`（5 条手填样本：Kickstarter × 2 + IT之家 × 3）
- `scripts/01_render_card.py`（5 条版渲染）
- 渲染过一张卡片（已丢失，旧版格式）