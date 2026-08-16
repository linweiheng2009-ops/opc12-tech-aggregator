#!/usr/bin/env python3
"""
OPC12 科技聚合 · 多尺寸卡片生成（4 尺寸 × 5 条/张）
输入：data/YYYY-MM-DD.json (10 条)
输出：photo/OPC12_科技聚合/YYYYMMDD_HHMM_{尺寸}_{cardN}.png

尺寸：
- xiaohongshu:  3:4   1140×1620   5 条/张 × 2 张  (小红书图文)
- friend:       1:1   1080×1080   5 条/张 × 2 张  (朋友圈)
- wechat_16x9:  16:9  1280×720    5 条/张 × 2 张  (公众号次条)
- wechat_top:   2.35:1  900×383   头条封面图 1 张 (公众号头条大图)
"""
import json, base64, sys
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PHOTO = Path("/Users/linweiheng/Documents/code poj/photo/OPC12_科技聚合")
PHOTO.mkdir(parents=True, exist_ok=True)

# ── 4 个尺寸 profile ──────────────────────────────────

# 源 AI 浓度优先级（头条图主推用）· DEC-014
SOURCE_AI_PRIORITY = {
    "qbitai": 5,      # 中文 AI 第1
    "thdecoder": 4,   # 英文 AI 第1
    "solidot": 3,     # 科技深度（常含 AI）
    "hn": 2,          # 英文科技风向（不定）
    "guokr": 1,       # 科技杂文
}

# 源 emoji 图标（P1-C 16:9 cell 用）· DEC-014
SOURCE_EMOJI = {
    "guokr": "🌿",
    "qbitai": "🧠",
    "solidot": "🛰️",
    "thdecoder": "🤖",
    "hn": "🔥",
}

def pick_top_item(items):
    """头条图主推挑 AI 浓度最高的 1 条"""
    if not items:
        return None
    return max(items, key=lambda x: SOURCE_AI_PRIORITY.get(x["source"], 0))

FORMATS = {
    "xiaohongshu": {
        "label": "小红书 3:4",
        "w": 1140, "h": 1620,
        "title_size": 64, "subtitle_size": 22, "tag_size": 22,
        "row_title_size": 18, "row_subtitle_size": 14, "src_size": 14,
        "thumb": 80, "row_gap": 12,
        "items_per_card": 5,
        "layout": "vertical",
        "tag_text": "DAILY · TECH 5",
        "title_text": "今日科技<br>5 件新鲜事",
        "subtitle_text": "每天 10 条 · 5 源精选",
        "hashtags": "#果壳 #爱范儿 #Solidot #少数派 #IT之家 #OPC12",
    },
    "friend": {
        "label": "朋友圈 1:1",
        "w": 1080, "h": 1080,
        "title_size": 52, "subtitle_size": 20, "tag_size": 20,
        "row_title_size": 17, "row_subtitle_size": 13, "src_size": 13,
        "thumb": 72, "row_gap": 10,
        "items_per_card": 5,
        "layout": "vertical",
        "tag_text": "DAILY · TECH 5",
        "title_text": "今日科技<br>5 件新鲜事",
        "subtitle_text": "每天 10 条 · 5 源精选",
        "hashtags": "#科技日报 #朋友圈 #OPC12",
    },
    "wechat_16x9": {
        "label": "公众号 16:9",
        "w": 1280, "h": 720,
        "title_size": 36, "subtitle_size": 18, "tag_size": 18,
        "row_title_size": 14, "row_subtitle_size": 11, "src_size": 11,
        "thumb": 56, "row_gap": 8,
        "items_per_card": 5,
        "layout": "horizontal",  # 5 条横排
        "tag_text": "DAILY · TECH 5",
        "title_text": "今日科技 5 件新鲜事",
        "subtitle_text": "每天 10 条 · 5 源精选",
        "hashtags": "#科技日报 #OPC12",
    },
    "wechat_top": {
        "label": "公众号头条 2.35:1",
        "w": 900, "h": 383,
        "title_size": 38, "subtitle_size": 16, "tag_size": 16,
        "row_title_size": 0, "row_subtitle_size": 0, "src_size": 0,
        "thumb": 0, "row_gap": 0,
        "items_per_card": 50,  # 头条图只 1 张，传 ≥len(items) 不拆
        "layout": "hero",
        "tag_text": "OPC12 · 今日头条",
        "title_text": "今日科技 5 件新鲜事",
        "subtitle_text": "每天 10 条 · 5 源精选 · 点击查看全文",
        "hashtags": "#OPC12",
    },
}

# ── HTML 模板（按 layout 分类） ──────────────────────

def html_vertical(p, items):
    """纵向布局：每条横排显示，thumb + meta"""
    rows = []
    for i, it in enumerate(items, 1):
        label = it.get("label", it["source"]).upper()
        color = it.get("color") or "#2C7BE5"
        emoji = SOURCE_EMOJI.get(it["source"], "📰")
        rows.append(f"""
        <div class="row">
          <div class="thumb"><div class="placeholder">{emoji}</div></div>
          <div class="meta">
            <div class="src" style="color:{color};border-color:{color};">{label}</div>
            <div class="title-row">{it['title']}</div>
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
    """横向布局（16:9 用）：标题占顶部 1/3，下方 5 条横排 grid"""
    rows = []
    for i, it in enumerate(items, 1):
        label = it.get("label", it["source"]).upper()
        color = it.get("color") or "#2C7BE5"
        emoji = SOURCE_EMOJI.get(it["source"], "📰")
        rows.append(f"""
        <div class="cell">
          <div class="src" style="color:{color};border-color:{color};">{emoji} {label}</div>
          <div class="title-row">{it['title']}</div>
        </div>""")
    return f"""
<div class="gradient"></div><div class="gradient2"></div>
<div class="wrap">
  <div class="header">
    <div class="tag">{p['tag_text']}</div>
    <div class="title">{p['title_text']}</div>
  </div>
  <div class="grid">{''.join(rows)}</div>
  <div class="footer">
    <div class="hashtags">{p['hashtags']}</div>
    <div class="date">{datetime.now().strftime('%Y.%m.%d')}</div>
  </div>
</div>"""

def html_hero(p, items):
    """头条封面图：智能挑 AI 浓度最高的 1 条作主推（P1-B）"""
    top = pick_top_item(items) if items else None
    if top:
        label = top.get("label", top["source"]).upper()
        color = top.get("color") or "#2C7BE5"
        emoji = SOURCE_EMOJI.get(top["source"], "📰")
        main_title = top["title"]
    else:
        label = ""
        color = "#2C7BE5"
        emoji = "📰"
        main_title = ""
    return f"""
<div class="gradient"></div>
<div class="wrap">
  <div class="left">
    <div class="tag" style="border-color:{color};color:{color};">{p['tag_text']}</div>
    <div class="title">{p['title_text']}</div>
    <div class="subtitle">{p['subtitle_text']}</div>
    <div class="src" style="color:{color};border-color:{color};">{emoji} {label}</div>
    <div class="top-title">{main_title}</div>
  </div>
  <div class="right">
    <div class="big-number">{datetime.now().strftime('%d')}</div>
    <div class="big-label">DAILY</div>
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
.wrap {{ position:relative; width:{W}px; min-height:{H}px; padding:{H*0.04:.0f}px {W*0.05:.0f}px {H*0.04:.0f}px;
  display:flex; flex-direction:column; }}
.tag {{ display:inline-block; padding:5px 14px; border:2px solid #00d4b8; border-radius:6px;
  font-family:"SF Mono","Menlo",monospace; font-size:{p['tag_size']}px; font-weight:600;
  color:#00d4b8; letter-spacing:2px; align-self:flex-start; }}
.title {{ font-family:"Noto Serif SC","Songti SC","SimSun",serif; font-size:{p['title_size']}px;
  font-weight:700; margin-top:12px; line-height:1.1; color:#fff; letter-spacing:-1px; }}
.subtitle {{ font-family:-apple-system,"PingFang SC",sans-serif; font-size:{p['subtitle_size']}px;
  margin-top:8px; color:#9ca3af; font-weight:400; }}
.divider {{ width:50px; height:3px; background:linear-gradient(90deg,#00d4b8,#2c7be5);
  margin-top:14px; border-radius:2px; }}
.list {{ margin-top:18px; display:flex; flex-direction:column; gap:{p['row_gap']}px; flex:1; }}
.row {{ display:flex; align-items:center; gap:14px; padding:8px;
  background:rgba(255,255,255,0.04); border-radius:10px; border:1px solid rgba(255,255,255,0.08); }}
.thumb {{ width:{p['thumb']}px; height:{p['thumb']}px; border-radius:8px; overflow:hidden;
  flex-shrink:0; background:#1a2030; display:flex; align-items:center; justify-content:center; }}
.placeholder {{ font-size:{int(p['thumb']*0.4)}px; font-weight:700; color:rgba(255,255,255,0.45); }}
.meta {{ flex:1; min-width:0; }}
.src {{ display:inline-block; font-family:"SF Mono",monospace; font-size:{p['src_size']}px;
  font-weight:700; padding:2px 6px; border:1.5px solid; border-radius:4px; letter-spacing:1px; margin-bottom:3px; }}
.title-row {{ font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
  font-size:{p['row_title_size']}px; font-weight:600; color:#fff; line-height:1.3;
  word-break:break-word; margin-bottom:2px; }}
.subtitle-row {{ font-family:-apple-system,"PingFang SC",sans-serif;
  font-size:{p['row_subtitle_size']}px; font-weight:400; color:#9ca3af; line-height:1.4;
  word-break:break-word; }}
.footer {{ margin-top:auto; padding-top:14px; display:flex; justify-content:space-between;
  align-items:center; font-family:"SF Mono",monospace; font-size:{p['src_size']}px; color:#6b7280; }}
.hashtags {{ color:#00d4b8; }}

/* 横向布局 16:9 专用 */
.header {{ display:flex; flex-direction:column; gap:6px; }}
.grid {{ flex:1; margin-top:14px; display:grid; grid-template-columns:repeat(5,1fr);
  grid-template-rows:1fr; gap:10px; }}
.cell {{ background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08);
  border-radius:8px; padding:12px 10px; display:flex; flex-direction:column; gap:8px;
  overflow:hidden; }}
.cell .title-row {{ flex:1; }}
.cell::after {{ content:""; flex:1; }}

/* 头条封面 900×383 专用 */
.wrap.hero {{ display:flex; flex-direction:row; padding:24px 32px; gap:20px; }}
.left {{ flex:1; display:flex; flex-direction:column; gap:8px; min-width:0; }}
.right {{ display:flex; flex-direction:column; align-items:flex-end; justify-content:flex-start; }}
.big-number {{ font-family:"Noto Serif SC","Songti SC",serif; font-size:120px; font-weight:700;
  color:#00d4b8; line-height:1; }}
.big-label {{ font-family:"SF Mono",monospace; font-size:14px; color:#9ca3af; letter-spacing:2px; }}
.top-title {{ font-family:-apple-system,"PingFang SC",sans-serif; font-size:14px;
  color:#fff; line-height:1.4; margin-top:auto; }}
"""

# ── 主流程 ──────────────────────────────────────────

def render_one(items, fmt_key, card_idx, total_cards):
    p = FORMATS[fmt_key]
    W, H = p["w"], p["h"]
    
    # 选 layout
    if p["layout"] == "vertical":
        body_html = html_vertical(p, items)
    elif p["layout"] == "horizontal":
        body_html = html_horizontal(p, items)
    elif p["layout"] == "hero":
        body_html = html_hero(p, items)
    else:
        body_html = html_vertical(p, items)
    
    # 头条图不用 body 容器（hero 自己 wrap）
    if p["layout"] == "hero":
        wrap_class = 'wrap hero'
    else:
        wrap_class = 'wrap'
    body_html = body_html.replace('class="wrap"', f'class="{wrap_class}"', 1)
    
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
            png = render_one(card_items, fmt_key, i, len(cards))
            size = png.stat().st_size
            print(f"   ✅ card {i}/{len(cards)}: {png.name} ({size:,} bytes)")
            results.append({"format": fmt_key, "card": i, "path": str(png)})
    
    print(f"\n💾 共生成 {len(results)} 张卡片")
    return results

if __name__ == "__main__":
    main()