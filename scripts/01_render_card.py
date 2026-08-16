#!/usr/bin/env python3
"""
OPC12 科技聚合 · 合成小红书风卡片（10 条/天 · 5 源 × 2）
输入：data/YYYY-MM-DD.json (10 条)
输出：photo/OPC12_科技聚合/YYYYMMDD_HHMM_科技聚合.png
"""
import json, base64, sys
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PHOTO = Path("/Users/linweiheng/Documents/code poj/photo/OPC12_科技聚合")
PHOTO.mkdir(parents=True, exist_ok=True)

W, H = 1140, 1620  # 3:4 小红书（10 条需要更高）

def img_b64(p):
    if not p: return ""
    p = Path(p)
    if not p.exists(): return ""
    ext = p.suffix.lstrip(".").lower()
    if ext == "jpg": ext = "jpeg"
    return f"data:image/{ext};base64,{base64.b64encode(p.read_bytes()).decode()}"

def main():
    today = DATA / f"{datetime.now().strftime('%Y-%m-%d')}.json"
    if not today.exists():
        print(f"❌ {today} 不存在，先跑 00_fetch.py")
        sys.exit(1)
    
    payload = json.load(open(today))
    items = payload["items"]
    print(f"📦 加载 {len(items)} 个产品")
    
    # 生成卡片 HTML
    rows = []
    for i, it in enumerate(items, 1):
        thumb = img_b64(it.get("image_path"))
        label = it.get("label", it["source"]).upper()
        color = it.get("color") or ("#FF6B35" if it["source"] == "kickstarter" else "#2C7BE5")
        rows.append(f"""
        <div class="row">
          <div class="thumb">{('<img src="'+thumb+'">') if thumb else f'<div class="placeholder">{i}</div>'}</div>
          <div class="meta">
            <div class="src" style="color:{color};border-color:{color};">{label}</div>
            <div class="title-row">{it['title']}</div>
            <div class="subtitle-row">{it.get('subtitle','')}</div>
          </div>
        </div>""")
    
    html = f"""<!doctype html>
<html><head><meta charset="utf-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:{W}px; min-height:{H}px; background:#0a0e1a; font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif; color:#fff; overflow-x:hidden; }}
.gradient {{ position:absolute; top:-200px; right:-200px; width:600px; height:600px; background:radial-gradient(circle,rgba(44,123,229,0.35) 0%,transparent 70%); pointer-events:none; }}
.gradient2 {{ position:absolute; bottom:-200px; left:-200px; width:500px; height:500px; background:radial-gradient(circle,rgba(0,200,180,0.25) 0%,transparent 70%); pointer-events:none; }}
.wrap {{ position:relative; width:{W}px; min-height:{H}px; padding:50px 60px 40px; display:flex; flex-direction:column; }}
.tag {{ display:inline-block; padding:6px 16px; border:2px solid #00d4b8; border-radius:6px; font-family:"SF Mono","Menlo",monospace; font-size:20px; font-weight:600; color:#00d4b8; letter-spacing:2px; align-self:flex-start; }}
.title {{ font-family:"Noto Serif SC","Songti SC","SimSun",serif; font-size:64px; font-weight:700; margin-top:16px; line-height:1.1; color:#fff; letter-spacing:-2px; }}
.subtitle {{ font-family:-apple-system,"PingFang SC",sans-serif; font-size:24px; margin-top:10px; color:#9ca3af; font-weight:400; }}
.divider {{ width:60px; height:3px; background:linear-gradient(90deg,#00d4b8,#2c7be5); margin-top:18px; border-radius:2px; }}
.list {{ margin-top:22px; display:flex; flex-direction:column; gap:10px; }}
.row {{ display:flex; align-items:center; gap:16px; padding:10px; background:rgba(255,255,255,0.04); border-radius:10px; border:1px solid rgba(255,255,255,0.08); }}
.thumb {{ width:80px; height:80px; border-radius:8px; overflow:hidden; flex-shrink:0; background:#1a2030; display:flex; align-items:center; justify-content:center; }}
.thumb img {{ width:100%; height:100%; object-fit:cover; }}
.placeholder {{ font-size:32px; font-weight:700; color:rgba(255,255,255,0.45); letter-spacing:0; }}
.meta {{ flex:1; min-width:0; }}
.src {{ display:inline-block; font-family:"SF Mono",monospace; font-size:14px; font-weight:700; padding:2px 6px; border:1.5px solid; border-radius:4px; letter-spacing:1.2px; margin-bottom:4px; }}
.title-row {{ font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif; font-size:18px; font-weight:600; color:#fff; line-height:1.3; word-break:break-word; margin-bottom:3px; }}
.subtitle-row {{ font-family:-apple-system,"PingFang SC",sans-serif; font-size:14px; font-weight:400; color:#9ca3af; line-height:1.4; word-break:break-word; }}
.footer {{ margin-top:auto; padding-top:18px; display:flex; justify-content:space-between; align-items:center; font-family:"SF Mono",monospace; font-size:14px; color:#6b7280; }}
.hashtags {{ color:#00d4b8; }}
</style></head><body>
<div class="gradient"></div>
<div class="gradient2"></div>
<div class="wrap">
  <div class="tag">DAILY · TECH 10</div>
  <div class="title">今日科技<br>10 件新鲜事</div>
  <div class="subtitle">每天 10 条 · 5 源精选</div>
  <div class="divider"></div>
  <div class="list">{''.join(rows)}</div>
  <div class="footer">
    <div class="hashtags">#果壳 #爱范儿 #Solidot #少数派 #IT之家 #OPC12</div>
    <div class="date">{datetime.now().strftime('%Y.%m.%d')}</div>
  </div>
</div>
</body></html>"""
    
    out_html = ROOT / "data" / "_render.html"
    out_html.write_text(html, encoding="utf-8")
    
    # 用 Playwright 截图
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=2)
        page = ctx.new_page()
        page.goto(f"file://{out_html}", wait_until="networkidle", timeout=15000)
        # 自适应高度：截到 body 真实高度
        body_h = page.evaluate("document.body.scrollHeight")
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        out_png = PHOTO / f"{ts}_科技聚合.png"
        page.screenshot(path=str(out_png), clip={"x":0,"y":0,"width":W,"height":min(body_h, 3000)})
        browser.close()
    
    print(f"✅ 卡片已生成: {out_png}")
    print(f"   大小: {out_png.stat().st_size} bytes")

if __name__ == "__main__":
    main()