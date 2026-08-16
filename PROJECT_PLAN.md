# OPC 12 · PROJECT_PLAN（路线图）

> 2026-08-16 立项，**当前阶段：MVP 跑通** ✅

---

## Phase 0 · 决策 ✅（2026-08-16）

- [x] 5 源选定（含 2 个替换 DEC-002/003）
- [x] 抓取策略定（RSS > JSON API > Playwright）
- [x] 卡片规格定（3:4 / 10 条 / 5 源配色）

---

## Phase 1 · MVP ✅（2026-08-16）

- [x] `00_fetch.py` 写好（5 源 × 2 条 = 10 条）
- [x] `01_render_card.py` 改好（5 → 10 条）
- [x] 全链路跑通：fetch → data/2026-08-16.json → render → 1.2MB PNG
- [x] README / DECISIONS / PROJECT_PLAN / TODO / DONE 5 个文档骨架

---

## Phase 2 · 自动化（✅ 已完成 2026-08-16）

- [x] **cron 架构**（DEC-008）：✅ GitHub Actions（仿 OPC 09）
- [x] **Workflow 配置**：`.github/workflows/daily.yml`（每天 UTC 00:00 跑 fetch + commit）
- [x] **本地 launchd**：每天 SGT 08:30 跑 render（git pull + 渲染 + PNG）
- [x] **目录名改**（DEC-009）：`12_科技聚合_Kickstarter_IT之家` → `12_科技聚合_科技资讯5源`
- [x] **GitHub repo**：https://github.com/linweiheng2009-ops/opc12-tech-aggregator
- [x] **OPC 主 README 索引加 12_**

---

## Phase 3 · 卡片升级（**P1**）

- [ ] **缩略图**：fetch 抓每个源的 article banner → 本地 `data/YYYY-MM-DD/images/`，render 优先用
  - 果壳：detail page `og:image`
  - 爱范儿：RSS `<enclosure>` 或 `<content:encoded>` 里第一张图
  - Solidot：RSS `<description>` 里第一张图
  - 少数派：API `banner` + `banner_for_desktop`（直接用 URL）
  - IT之家：RSS `<description>` 里第一张图
- [ ] **多尺寸输出**：
  - 小红书 3:4（已有）
  - 公众号 16:9 / 2.25:1（头条/次条）
  - 朋友圈 4:3 / 1:1
- [ ] **深色 / 浅色主题切换**
- [ ] **历史归档页**：把每日 10 条拼成月份卡片墙

---

## Phase 4 · 流量分发（**P2**）

- [ ] 推送到 ChainThink 公众号草稿箱（用 publish_to_chainthink.py）
  - 文章标题：「今日科技 10 件新鲜事 · YYYY-MM-DD」
  - 内容：5 源分组 + 每条链接
- [ ] 嵌入到老蔚社圈 `laowe.club/tech` 板块（如果恒哥要做）
- [ ] 同步发到恒哥的小红书（手动 / 自动 API 都不确定，看平台政策）

---

## Phase 5 · 数据沉淀（**P3**）

- [ ] 累计 JSON 历史聚合（每月 1 个 monthly.json，含 top 文章 / 平均热度）
- [ ] 关键词趋势分析（每周 Top 20 词频）
- [ ] 源健康度看板（每源抓取成功率 / 平均 description 长度）

---

## 长期愿景

**「一人公司的科技资讯官」**——每天早上一张卡片，告诉恒哥"今天该看什么"。

不堆量、不喊口号、不刷屏。**有用的 10 条 > 无用的 100 条。**