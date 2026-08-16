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