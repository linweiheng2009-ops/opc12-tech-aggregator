# OPC 12 · 科技聚合（5 源 × 2 条/天 = 10 条）

> 每天自动抓取 **5 个科技资讯源**，每个源取 top2，合成 **小红书风 3:4 卡片**，可发小红书 / 公众号 / 朋友圈

**当前状态**: ✅ MVP 已跑通（fetch + render 全链路，10 条/天）

---

## 🎯 项目定位

- **每天 10 条科技资讯**：5 源 × 2 条
- **一张 3:4 卡片**（1140×1620px，小红书同款比例）
- **展示内容**：序号 + 源标签（配色）+ 主标题 + 概要描述
- **定时任务**：cron 每日自动跑（待恒哥确认架构）

---

## 📡 5 个数据源

| # | 源 | 类型 | 抓取方式 | 标签色 | 状态 |
|---|---|---|---|---|---|
| 1 | **果壳** guokr.com | 综合科普 | Playwright 首页 → 详情页 description | 🟢 #83C176 | ✅ |
| 2 | **爱范儿** ifanr.com | 数字潮牌 | RSS feed | 🔴 #F25C54 | ✅ |
| 3 | **Solidot** solidot.org | 科技深度 | RSS index.rss | 🔵 #1F6FEB | ✅ |
| 4 | **少数派** sspai.com | 科技生活方式 | JSON API | 🟠 #D9472A | ✅ |
| 5 | **IT之家** ithome.com | 数码综合 | RSS /rss/ | 🔵 #2C7BE5 | ✅ |

> ⚠️ **DEC-002**：恒哥原本指定"虎嗅"，但虎嗅全站被阿里云 WAF 滑块验证挡死（Playwright + stealth 破不了），替换为 **少数派**（科技生活方式调性最近 + 有 JSON API）。
>
> ⚠️ **DEC-003**：恒哥原本指定"36氪"，但 36kr 在新加坡 IP 被 Cloudflare 风控（Playwright 拿到 3.7KB 空页面），替换为 **Solidot**（科技深度新闻 + RSS 100% 稳定）。
>
> 两个替换都等恒哥 review，可随时改回。

---

## 🗂 目录结构

```
12_科技聚合_科技资讯5源/
├── README.md            ← 本文件
├── PROJECT_PLAN.md      ← 路线图
├── DONE.md              ← 已完成
├── TODO.md              ← 待办
├── docs/
│   └── DECISIONS.md     ← 关键决策记录
├── scripts/
│   ├── 00_fetch.py      ← 抓取 5 源 → data/YYYY-MM-DD.json
│   └── 01_render_card.py ← data/YYYY-MM-DD.json → 3:4 卡片 PNG
└── data/
    ├── YYYY-MM-DD.json  ← 每日抓取结果（cron 产出）
    ├── _render.html     ← render 脚本中间产物
    └── today.json       ← 旧版样本（已废弃，新版 fetch 不读）
```

> ⚠️ **目录名待改**：`12_科技聚合_科技资讯5源` 这个名字是 8-15 立项时基于旧 2 源（Kickstarter + IT之家）起的，**新 5 源里没 Kickstarter**。建议改名 `12_科技聚合_科技资讯5源` 或 `12_科技聚合_每日十条`，等恒哥拍板。

---

## 🚀 使用方法

### 手动跑一次

```bash
cd ~/Documents/OPC/12_科技聚合_科技资讯5源

# 抓数据（5 源 × 2 条 = 10 条）→ data/YYYY-MM-DD.json
python3 scripts/00_fetch.py

# 生成卡片 → ~/Documents/code poj/photo/OPC12_科技聚合/
python3 scripts/01_render_card.py
```

### 数据格式

`data/YYYY-MM-DD.json`：

```json
{
  "date": "2026-08-16",
  "generated_at": "2026-08-16T11:31:13",
  "total": 10,
  "sources": [{"source": "guokr", "label": "果壳", "count": 2}, ...],
  "items": [
    {
      "source": "guokr",
      "label": "果壳",
      "color": "#83C176",
      "title": "别再去西餐厅当冤大头！",
      "url": "https://www.guokr.com/article/469931",
      "subtitle": "不知道大家有没有这样的困惑..."
    },
    ...
  ]
}
```

### 卡片输出

`~/Documents/code poj/photo/OPC12_科技聚合/YYYYMMDD_HHMM_科技聚合.png`

- 比例：3:4（小红书）
- 尺寸：2280 × 3240px（1140×1620 @ 2x device pixel ratio）
- 文件大小：~1.2MB

---

## 🛠 技术栈

- **Python 3.9+**（系统自带）
- **urllib**（标准库）+ **xml.etree.ElementTree**（RSS 解析）
- **playwright**（headless Chromium）
- **JSON API**（少数派）

无 Node.js / 无数据库 / 无服务器依赖。

---

## ⏰ 定时任务

**待定**。两个候选方案：

| 方案 | 优点 | 缺点 |
|---|---|---|
| **A. GitHub Actions**（仿 OPC 09） | 免费、cron 精确、稳定 | 数据要 commit 推送，数据源访问受 GitHub IP 影响（36kr 风控可能例外） |
| **B. 本地 launchd / OpenClaw cron** | 跑在恒哥 Mac，数据直存本地 | Mac 不在线就漏跑 |

待恒哥拍板（建议 A，跟 OPC 09 同套）。

---

## 📝 后续规划

见 `PROJECT_PLAN.md`。

主要方向：
1. **P0**：配 cron / 改目录名 / 加缩略图（fetch 抓 article banner → 本地）
2. **P1**：输出多尺寸卡片（公众号 16:9 / 朋友圈 4:3 / 小红书 3:4）
3. **P2**：可选接入公众号 ChainThink 草稿箱 / 老蔚社圈科技板块

---

## 维护者

小蔚（AI 助手）· 恒哥 review & 拍板