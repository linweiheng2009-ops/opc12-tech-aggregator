#!/usr/bin/env python3
"""
OPC12 科技聚合 · 多尺寸卡片生成（4 尺寸 · 不显示源名 · 10 条/张 · 头条智能主推）
输入：data/YYYY-MM-DD.json (10 条)
输出：photo/OPC12_科技聚合/YYYYMMDD_HHMM_{尺寸}_cardN.png

设计原则（DEC-016 · 2026-08-16 恒哥拍板）：
1. 不显示数据源名称（果壳/量子位/Solidot/The Decoder/Hacker News 都不显示）
2. 小红书 / 朋友圈 单张 10 条/天全展示
3. 公众号 16:9 受限于横向空间，仍 5 条/张 × 2 张 = 10 条
4. 头条图重设计：单条主推居中 + 大字日期 + 简洁 tag
5. 英文资讯已在 fetch 阶段翻译为中文（fetch 03_translate.py）
"""
import json, sys
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PHOTO = Path("/Users/linweiheng/Documents/code poj/photo/OPC12_科技聚合")
PHOTO.mkdir(parents=True, exist_ok=True)

# ── 源 AI 浓度优先级（头条图主推用）· DEC-014 ──────

SOURCE_AI_PRIORITY = {
    "qbitai": 5, "thdecoder": 4, "solidot": 3, "hn": 2, "guokr": 1,
}

def pick_top_item(items):
    """头条图主推挑 AI 浓度最高的 1 条"""
    if not items:
        return None
    return max(items, key=lambda x: SOURCE_AI_PRIORITY.get(x["source"], 0))

# ── 4 个尺寸 profile（DEC-016 调整后） ──────────────

FORMATS = {
    "xiaohongshu": {
        "label": "小红书 3:4",
        "w": 1140, "h": 1620,
        "title_size": 56, "subtitle_size": 20, "tag_size": 20,
        "row_title_size": 18, "row_subtitle_size": 13, "num_size": 28,
        "thumb": 56, "row_gap": 6,
        "items_per_card": 10,
        "layout": "vertical",
        "tag_text": "DAILY · TECH 10",
        "title_text": "今日科技<br>10 件新鲜事",
        "subtitle_text": "每天精选 10 条 · 一张看完",
        "hashtags": "#科技日报 #AI资讯 #OPC12",
    },
    "friend": {
        "label": "朋友圈 1:1",
        "w": 1080, "h": 1080,
        "title_size": 48, "subtitle_size": 18, "tag_size": 18,
        "row_title_size": 17, "row_subtitle_size": 12, "num_size": 26,
        "thumb": 50, "row_gap": 5,
        "items_per_card": 10,
        "layout": "vertical",
        "tag_text": "DAILY · TECH 10",
        "title_text": "今日科技<br>10 件新鲜事",
        "subtitle_text": "每天精选 10 条",
        "hashtags": "#科技日报 #AI资讯 #OPC12",
    },
    "wechat_16x9": {
        "label": "公众号 16:9",
        "w": 1280, "h": 720,
        "title_size": 28, "subtitle_size": 13, "tag_size": 16,
        "row_title_size": 12, "row_subtitle_size": 10, "num_size": 20,
        "thumb": 0, "row_gap": 4,
        "items_per_card": 10,
        "layout": "horizontal",
        "tag_text": "DAILY · TECH 10",
        "title_text": "今日科技 10 件新鲜事",
        "subtitle_text": "一张看完 · 10 条精选",
        "hashtags": "#科技日报 #OPC12",
    },
    "wechat_top": {
        "label": "公众号头条 2.35:1",
        "w": 900, "h": 383,
        "title_size": 0, "subtitle_size": 0, "tag_size": 16,
        "row_title_size": 0, "row_subtitle_size": 0, "num_size": 0,
        "thumb": 0, "row_gap": 0,
        "items_per_card": 50,
        "layout": "hero",
        "tag_text": "今日科技头条",
        "title_text": "",
        "subtitle_text": "",
        "hashtags": "",
    },
}

# ── HTML 模板（按 layout 分类） ──────────────────────

def html_vertical(p, items):
    """纵向布局：去掉源名，每条 = 序号 + 标题 + 概要"""
    rows = []
    for i, it in enumerate(items, 1):
        score = it.get('score')
        heat_html = f'<span class="heat">🔥 {score}</span>' if score else ''
        rows.append(f"""
        <div class="row">
          <div class="num">{i:02d}</div>
          <div class="meta">
            <div class="title-row">{it['title']} {heat_html}</div>
            <div class="subtitle-row">{it.get('subtitle','')}</div>
          </div>
        </div>""")
    return f"""
<div class="gradient"></div><div class="gradient2"></div>
<div class="wrap">
  <div class="tag">{p['tag_text']}</div>
  <div class="title">{p['title_text']}</div>
  <div class="subtitle">{p['subtitle_text']}</div>
  <div class="divider"></div>
  <div class="list">{''.join(rows)}</div>
  <div class="footer">
    <div class="hashtags">{p['hashtags']}</div>
    <div class="date">{datetime.now().strftime('%Y.%m.%d')}</div>
  </div>
</div>"""

def html_horizontal(p, items):
    """横向布局（16:9 用）：5 条横排 grid，每条 = 序号 + 标题 + 概要"""
    rows = []
    for i, it in enumerate(items, 1):
        sub = it.get('subtitle', '')
        score = it.get('score')
        # 热度标签：有 score 的显示 🔥 分数
        heat_html = f'<span class="heat">🔥 {score}</span>' if score else ''
        rows.append(f"""
        <div class="cell">
          <div class="num">{i:02d}</div>
          <div class="title-row">{it['title']} {heat_html}</div>
          <div class="subtitle-row">{sub}</div>
        </div>""")
    return f"""
<div class="gradient"></div><div class="gradient2"></div>
<div class="wrap">
  <div class="header">
    <div class="tag">{p['tag_text']}</div>
    <div class="title">{p['title_text']}</div>
    <div class="subtitle">{p['subtitle_text']}</div>
  </div>
  <div class="grid">{''.join(rows)}</div>
  <div class="footer">
    <div class="hashtags">{p['hashtags']}</div>
    <div class="date">{datetime.now().strftime('%Y.%m.%d')}</div>
  </div>
</div>"""

def html_hero(p, items):
    """头条封面图重设计（DEC-016）：单条主推占左 70%，右 30% 大字日期"""
    top = pick_top_item(items) if items else None
    main_title = (top["title"] if top else "今日科技 10 件新鲜事")
    main_subtitle = (top.get("subtitle", "")[:120] if top else "每天精选 10 条")
    return f"""
<div class="gradient"></div>
<div class="wrap hero">
  <div class="hero-left">
    <div class="hero-tag">{p['tag_text']}</div>
    <div class="hero-title">{main_title}</div>
    <div class="hero-subtitle">{main_subtitle}</div>
  </div>
  <div class="hero-right">
    <div class="hero-date">{datetime.now().strftime('%m/%d')}</div>
    <div class="hero-cta">查看 10 条全文 →</div>
  </div>
</div>"""

# ── 样式（按 format 套用） ────────────────────────────

def style_for(p):
    W, H = p["w"], p["h"]
    return f"""
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:{W}px; min-height:{H}px; background:#0a0e1a;
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;
  color:#fff; overflow:hidden; }}
.gradient {{ position:absolute; top:-200px; right:-200px; width:600px; height:600px;
  background:radial-gradient(circle,rgba(44,123,229,0.35) 0%,transparent 70%); pointer-events:none; }}
.gradient2 {{ position:absolute; bottom:-200px; left:-200px; width:500px; height:500px;
  background:radial-gradient(circle,rgba(0,200,180,0.25) 0%,transparent 70%); pointer-events:none; }}
.wrap {{ position:relative; width:{W}px; min-height:{H}px; padding:{H*0.025:.0f}px {W*0.035:.0f}px {H*0.02:.0f}px;
  display:flex; flex-direction:column; }}
.tag {{ display:inline-block; padding:4px 12px; border:2px solid #00d4b8; border-radius:6px;
  font-family:"SF Mono","Menlo",monospace; font-size:{p['tag_size']}px; font-weight:600;
  color:#00d4b8; letter-spacing:2px; align-self:flex-start; }}
.title {{ font-family:"Noto Serif SC","Songti SC","SimSun",serif; font-size:{p['title_size']}px;
  font-weight:700; margin-top:8px; line-height:1.1; color:#fff; letter-spacing:-1px; }}
.subtitle {{ font-family:-apple-system,"PingFang SC",sans-serif; font-size:{p['subtitle_size']}px;
  margin-top:4px; color:#9ca3af; font-weight:400; }}
.divider {{ width:40px; height:2px; background:linear-gradient(90deg,#00d4b8,#2c7be5);
  margin-top:8px; border-radius:2px; }}
.list {{ margin-top:8px; display:flex; flex-direction:column; gap:{p['row_gap']}px; flex:1; justify-content:space-between; }}
.row {{ display:flex; align-items:center; gap:10px; padding:7px 10px;
  background:rgba(255,255,255,0.04); border-radius:6px; border:1px solid rgba(255,255,255,0.08); }}
.num {{ width:{p['num_size']}px; height:{p['num_size']}px; flex-shrink:0; display:flex; align-items:center; justify-content:center;
  font-family:"SF Mono","Menlo",monospace; font-size:{int(p['num_size']*0.55)}px; font-weight:700;
  color:#00d4b8; background:rgba(0,212,184,0.1); border:1px solid rgba(0,212,184,0.3); border-radius:6px; }}
.meta {{ flex:1; min-width:0; }}
.title-row {{ font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
  font-size:{p['row_title_size']}px; font-weight:600; color:#fff; line-height:1.3;
  word-break:break-word; margin-bottom:2px; }}
.subtitle-row {{ font-family:-apple-system,"PingFang SC",sans-serif;
  font-size:{p['row_subtitle_size']}px; font-weight:400; color:#9ca3af; line-height:1.4;
  word-break:break-word; }}
.footer {{ margin-top:6px; padding-top:8px; display:flex; justify-content:space-between;
  align-items:center; font-family:"SF Mono",monospace; font-size:{int(p['row_subtitle_size']*0.9)}px; color:#6b7280; }}
.hashtags {{ color:#00d4b8; }}

/* 16:9 横向布局 · 单张 10 条（2 行 × 5 列）*/
.header {{ display:flex; flex-direction:column; gap:4px; }}
.grid {{ flex:1; margin-top:6px; display:grid; grid-template-columns:repeat(5,1fr);
  grid-template-rows:repeat(2,1fr); gap:4px; }}
.cell {{ background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08);
  border-radius:5px; padding:6px 7px; display:flex; flex-direction:column; gap:3px; overflow:hidden; }}
.cell .title-row {{ font-size:{p['row_title_size']}px; font-weight:600; color:#fff; line-height:1.3;
  word-break:break-word; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;
  overflow:hidden; }}
.cell .subtitle-row {{ font-size:{p['row_subtitle_size']}px; color:#9ca3af; line-height:1.35;
  word-break:break-word; overflow:hidden; display:-webkit-box; -webkit-line-clamp:12;
  -webkit-box-orient:vertical; flex:1; }}
.cell .num {{ width:20px; height:20px; flex-shrink:0; display:flex; align-items:center; justify-content:center;
  font-family:"SF Mono","Menlo",monospace; font-size:11px; font-weight:700;
  color:#00d4b8; background:rgba(0,212,184,0.1); border:1px solid rgba(0,212,184,0.3); border-radius:3px; }}

/* 头条图 hero（DEC-016 重设计） */
.wrap.hero {{ display:flex; flex-direction:row; padding:24px 32px; gap:24px; align-items:stretch; }}
.hero-left {{ flex:7; display:flex; flex-direction:column; gap:8px; min-width:0; }}
.hero-right {{ flex:3; display:flex; flex-direction:column; align-items:flex-end; justify-content:space-between;
  border-left:1px solid rgba(0,212,184,0.3); padding-left:20px; }}
.hero-tag {{ display:inline-block; padding:4px 12px; border:2px solid #00d4b8; border-radius:5px;
  font-family:"SF Mono",monospace; font-size:14px; font-weight:600; color:#00d4b8;
  letter-spacing:2px; align-self:flex-start; }}
.hero-title {{ font-family:"Noto Serif SC","Songti SC",serif; font-size:24px; font-weight:700;
  color:#fff; line-height:1.25; word-break:break-word; margin-top:4px; }}
.hero-subtitle {{ font-family:-apple-system,"PingFang SC",sans-serif; font-size:13px;
  color:#9ca3af; line-height:1.5; word-break:break-word; margin-top:auto; }}
.hero-date {{ font-family:"Noto Serif SC","Songti SC",serif; font-size:80px; font-weight:700;
  color:#00d4b8; line-height:1; letter-spacing:-2px; }}
.hero-cta {{ font-family:"SF Mono",monospace; font-size:12px; color:#9ca3af; letter-spacing:1px; }}
"""

# ── 主流程 ──────────────────────────────────────────

def render_one(items, fmt_key, card_idx):
    p = FORMATS[fmt_key]
    W, H = p["w"], p["h"]
    
    if p["layout"] == "vertical":
        body_html = html_vertical(p, items)
    elif p["layout"] == "horizontal":
        body_html = html_horizontal(p, items)
    elif p["layout"] == "hero":
        body_html = html_hero(p, items)
    else:
        body_html = html_vertical(p, items)
    
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><style>{style_for(p)}</style></head>
<body>{body_html}</body></html>"""
    
    out_html = DATA / f"_render_{fmt_key}_{card_idx}.html"
    out_html.write_text(html, encoding="utf-8")
    
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    out_png = PHOTO / f"{ts}_{fmt_key}_card{card_idx}.png"
    
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=2)
        page = ctx.new_page()
        page.goto(f"file://{out_html}", wait_until="networkidle", timeout=15000)
        body_h = page.evaluate("document.body.scrollHeight")
        page.screenshot(path=str(out_png), clip={"x":0,"y":0,"width":W,"height":min(body_h, 4000)})
        browser.close()
    
    return out_png

def main():
    today = datetime.now().strftime('%Y-%m-%d')
    today_file = DATA / f"{today}.json"
    if not today_file.exists():
        print(f"❌ {today_file} 不存在，先跑 00_fetch.py")
        sys.exit(1)
    
    payload = json.load(open(today_file))
    items = payload["items"]
    print(f"📦 加载 {len(items)} 条")
    
    results = []
    for fmt_key, p in FORMATS.items():
        per = p["items_per_card"]
        cards = [items[i:i+per] for i in range(0, len(items), per)]
        print(f"\n🎨 {p['label']}: {len(cards)} 张 × {per} 条/张")
        for i, card_items in enumerate(cards, 1):
            png = render_one(card_items, fmt_key, i)
            size = png.stat().st_size
            print(f"   ✅ card {i}/{len(cards)}: {png.name} ({size:,} bytes)")
            results.append({"format": fmt_key, "card": i, "path": str(png)})
    
    print(f"\n💾 共生成 {len(results)} 张卡片")
    return results

if __name__ == "__main__":
    main()