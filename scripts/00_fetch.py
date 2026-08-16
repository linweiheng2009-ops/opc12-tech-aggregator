#!/usr/bin/env python3
"""
OPC12 科技聚合 · 抓取 5 源 × 2 条 = 10 条/天
输入：5 个源（RSS / JSON API / Playwright 首页）
输出：data/YYYY-MM-DD.json (10 条)
"""
import json, re, sys, traceback
from pathlib import Path
from datetime import datetime
import urllib.request, urllib.error
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# 5 源配置（DEC-001）
SOURCES = [
    {
        "id": "guokr",
        "label": "果壳",
        "color": "#83C176",
        "type": "playwright_list_with_detail",
        "list_url": "https://www.guokr.com/",
        "selector": 'a[href*="/article/"]',
        "detail_desc_sel": 'meta[name="description"]',
    },
    {
        "id": "ifanr",
        "label": "爱范儿",
        "color": "#F25C54",
        "type": "rss",
        "url": "https://www.ifanr.com/feed",
    },
    {
        "id": "solidot",
        "label": "Solidot",
        "color": "#1F6FEB",
        "type": "rss",
        "url": "https://www.solidot.org/index.rss",
    },
    {
        "id": "sspai",
        "label": "少数派",
        "color": "#D9472A",
        "type": "json_api",
        "url": "https://sspai.com/api/v1/articles?offset=0&limit=10",
    },
    {
        "id": "ithome",
        "label": "IT之家",
        "color": "#2C7BE5",
        "type": "rss",
        "url": "https://www.ithome.com/rss/",
    },
]

PER_SOURCE = 2  # 每源 2 条 = 10 条/天
FETCH_TIMEOUT = 25

# ──── 抓取器 ──────────────────────────────────────────

def fetch_url(url, timeout=FETCH_TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def fetch_rss(src):
    """RSS 抓取（爱范儿 / IT之家）"""
    xml_text = fetch_url(src["url"])
    root = ET.fromstring(xml_text)
    items = []
    for item in root.findall(".//item"):
        title_el = item.find("title")
        link_el = item.find("link")
        desc_el = item.find("description")
        if title_el is None or link_el is None:
            continue
        title = (title_el.text or "").strip()
        link = (link_el.text or "").strip()
        desc = ""
        if desc_el is not None and desc_el.text:
            desc = re.sub(r"<[^>]+>", "", desc_el.text).strip()
            desc = re.sub(r"\s+", " ", desc)[:160]
        if not title or not link:
            continue
        items.append({
            "source": src["id"],
            "label": src["label"],
            "color": src["color"],
            "title": title,
            "url": link,
            "subtitle": desc,
        })
        if len(items) >= PER_SOURCE:
            break
    return items

def fetch_json_api(src):
    """JSON API 抓取（少数派）"""
    data = json.loads(fetch_url(src["url"]))
    items = []
    for art in data.get("list", [])[:PER_SOURCE]:
        title = (art.get("title") or "").strip()
        art_id = art.get("id")
        summary = (art.get("summary") or "").strip()
        if not title or not art_id:
            continue
        # json.loads 已自动把 \uXXXX 解为中文字符串，不要再 unicode_escape 一次
        summary = re.sub(r"\s+", " ", summary)[:160]
        items.append({
            "source": src["id"],
            "label": src["label"],
            "color": src["color"],
            "title": title,
            "url": f"https://sspai.com/post/{art_id}",
            "subtitle": summary,
        })
    return items

def fetch_playwright_list(src):
    """Playwright 抓首页列表 + 详情页 description（果壳 / 36氪）"""
    from playwright.sync_api import sync_playwright
    
    items = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
            locale="zh-CN", timezone_id="Asia/Shanghai",
        )
        page = ctx.new_page()
        page.set_default_timeout(20000)
        
        # 1. 抓列表
        try:
            page.goto(src["list_url"], wait_until="commit", timeout=60000)
        except Exception:
            # commit 也失败则用 domcontentloaded 再试
            try:
                page.goto(src["list_url"], wait_until="domcontentloaded", timeout=30000)
            except Exception:
                pass
        page.wait_for_timeout(6000)
        
        if src.get("needs_scroll"):
            for _ in range(3):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)
        
        # 多个 selector fallback
        selectors = [src["selector"]]
        if src["id"] == "guokr":
            selectors += ['article h2 a', 'article h3 a', '.article-title a', 'h2 a', 'h3 a']
        
        locs = None
        for sel in selectors:
            try:
                cnt = page.locator(sel).count()
                if cnt >= PER_SOURCE:
                    locs = page.locator(sel)
                    break
            except Exception:
                pass
        if locs is None:
            # fallback：用第一个 selector（哪怕 0 条）
            locs = page.locator(selectors[0])
        
        seen = set()
        candidates = []
        max_iter = max(PER_SOURCE * 5, 15)
        for i in range(min(locs.count(), max_iter)):
            try:
                t = locs.nth(i).inner_text(timeout=800).strip()
                h = locs.nth(i).get_attribute("href") or ""
                if not t or len(t) < 8 or len(t) > 120 or not h or h in seen:
                    continue
                if "/article/" not in h and "/p/" not in h and "/info" not in h:
                    continue
                seen.add(h)
                if not h.startswith("http"):
                    base = src["list_url"]
                    h = base.rstrip("/") + (h if h.startswith("/") else "/" + h)
                candidates.append({"title": t, "url": h})
                if len(candidates) >= PER_SOURCE:
                    break
            except Exception:
                pass
        
        # 2. 抓详情页 description
        for cand in candidates:
            desc = ""
            try:
                page.goto(cand["url"], wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(2500)
                meta_el = page.locator(src["detail_desc_sel"]).first
                if meta_el.count() > 0:
                    desc = meta_el.get_attribute("content") or ""
                    desc = re.sub(r"\s+", " ", desc).strip()[:160]
                if not desc:
                    p_el = page.locator("p").first
                    if p_el.count() > 0:
                        desc = (p_el.inner_text(timeout=1000) or "").strip()[:160]
            except Exception:
                pass
            items.append({
                "source": src["id"],
                "label": src["label"],
                "color": src["color"],
                "title": cand["title"],
                "url": cand["url"],
                "subtitle": desc,
            })
        
        browser.close()
    return items

# ──── 主流程 ──────────────────────────────────────────

def main():
    DATA.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    out = DATA / f"{today}.json"
    
    all_items = []
    summary = []
    for src in SOURCES:
        print(f"📡 {src['label']:<6}", end=" ", flush=True)
        try:
            if src["type"] == "rss":
                items = fetch_rss(src)
            elif src["type"] == "json_api":
                items = fetch_json_api(src)
            elif src["type"] == "playwright_list_with_detail":
                items = fetch_playwright_list(src)
            else:
                items = []
            print(f"✅ {len(items)} 条")
            all_items.extend(items)
            summary.append({"source": src["id"], "label": src["label"], "count": len(items)})
        except Exception as e:
            print(f"❌ {type(e).__name__}: {str(e)[:80]}")
            traceback.print_exc(limit=2)
            summary.append({"source": src["id"], "label": src["label"], "count": 0, "error": str(e)[:80]})
    
    # 输出
    payload = {
        "date": today,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "total": len(all_items),
        "sources": summary,
        "items": all_items,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n💾 {out}")
    print(f"   {len(all_items)} 条 / 目标 10 条")
    
    if len(all_items) < 10:
        print(f"⚠️  实际 {len(all_items)} < 10，目标未达成")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())