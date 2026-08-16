# OPC 12 · TODO（待办清单）

> 按优先级 + 状态组织

---

## P0 · 决策拍板（恒哥 11:41 拍板）

- [x] **DEC-008 cron 架构** → ✅ 选 **GitHub Actions**（仿 OPC 09）
- [x] **DEC-009 目录名** → ✅ 改名 **`12_科技聚合_科技资讯5源`**
- [x] **DEC-002/003 源替换** → ✅ 接受（虎嗅→少数派 / 36kr→Solidot）

## P0 · 立刻要做

- [x] 更新 OPC 主 README（~/Documents/OPC/README.md）加 12_ 索引
- [x] 改名 12_科技聚合_Kickstarter_IT之家 → 12_科技聚合_科技资讯5源
- [ ] 建 GitHub repo + Actions workflow + 本地 launchd render
- [ ] 验证全链路

---

## P1 · 缩略图（卡片美观）

- [ ] 果壳 og:image 抓取
- [ ] 爱范儿 RSS enclosure/content:encoded 第一张图
- [ ] Solidot RSS description 第一张图
- [ ] 少数派 API banner 字段直接 URL（最简单）
- [ ] IT之家 RSS description 第一张图
- [ ] fetch 加 download 缩略图 → data/YYYY-MM-DD/images/{id}.jpg

---

## P2 · 多尺寸输出

- [ ] 公众号 16:9 横幅版
- [ ] 朋友圈 1:1 方形版
- [ ] 公众号头条 2.25:1 大图版

---

## P3 · 自动化 & 分发

- [ ] cron workflow 配好后跑 1 周看稳定性
- [ ] 推送到 ChainThink 草稿箱
- [ ] 嵌入老蔚社圈

---

## P3 · 数据沉淀

- [ ] 累计 JSON 历史归档
- [ ] 源健康度看板
- [ ] 关键词趋势分析

---

## 临时发现

- [ ] 今日（2026-08-16）已抓取 10 条成功 → `data/2026-08-16.json`
- [ ] 卡片 PNG 已生成 → `~/Documents/code poj/photo/OPC12_科技聚合/20260816_1137_科技聚合.png`（1.2MB）
- [ ] today.json（旧版 5 条样本）保留为历史记录，新版 fetch 不读它