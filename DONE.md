# OPC 12 · DONE（已完成）

> 倒序时间，最新的在上面

---

## 2026-08-16 11:43 · 恒哥拍板 + 自动化全跑通 ✅

### 恒哥拍板 3 件事
- DEC-008 cron 架构 → ✅ GitHub Actions
- DEC-009 目录名 → ✅ 改为 `12_科技聚合_科技资讯5源`
- DEC-002/003 源替换 → ✅ 接受（虎嗅→少数派 / 36kr→Solidot）

### 自动化全链路
- ✅ GitHub repo 创建：https://github.com/linweiheng2009-ops/opc12-tech-aggregator
- ✅ GitHub Actions workflow：`.github/workflows/daily.yml`（UTC 00:00 跑 fetch）
- ✅ workflow_dispatch 手动触发一次成功：commit `ae7728f` "data: daily snapshot 2026-08-16"
- ✅ 本地 launchd：`~/Library/LaunchAgents/com.opc12.tech.render.plist`（SGT 08:30 跑 render）
- ✅ 启动脚本：`scripts/run_render.sh`（git pull + render）
- ✅ 手动跑脚本成功：生成 `20260816_1143_科技聚合.png`（1.2MB）

### 文档同步
- ✅ OPC 主 README 索引已同步改名字
- ✅ README / DECISIONS / PROJECT_PLAN / TODO 5 个文件状态同步

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
## 2026-08-16 15:13 · 换 3 个 AI 源 + 16:9 修复

### 恒哥拍板 B 方案（多换 1 个 Hacker News）
- DEC-013 · 3 源替换：爱范儿→量子位、少数派→The Decoder、IT之家→HN
- AI 浓度从 0~20% → **60%**（3/5 源 100% AI）

### 验证
- ✅ `00_fetch.py` 10 条全抓到（果壳2 + 量子位2 + Solidot2 + The Decoder2 + HN2）
- ✅ `02_render_multi.py` 7 张卡片生成
- ✅ 16:9 cell 高度修复（`grid-template-rows:1fr` + `.cell::after` 撑满）

### 新 5 源 sample（2026-08-16 15:12）
- 果壳：别再去西餐厅当冤大头 / AI 满篇的"不是……而是……"
- 量子位：WorkSwarm / 牛来！A社营收暴涨1400%
- Solidot：俄罗斯导弹使用 Jetson Orin / 年轻人不信任 AI 公司高管
- The Decoder：Optima AI benchmarking / 1/5 美国人委托 AI 做事
- Hacker News：Asus Bike Booster / Asynchronous I/O in DuckDB
