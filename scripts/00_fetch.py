#!/usr/bin/env python3
"""
OPC12 科技聚合 · 抓取 4 源（果壳已去掉）· 总量 10 条/天
DEC-018 · 2026-08-16 拍板：去掉果壳后采用 3+3+2+2 不均分布（AI 浓度 100%）

输入：4 个源（RSS）
输出：data/YYYY-MM-DD.json (10 条)
"""
import json, re, sys, traceback
from pathlib import Path
from datetime import datetime
import urllib.request, urllib.error
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# 4 源配置（DEC-018 · 去掉果壳）
# 每源条数：AI 浓度高的多取，AI 浓度低的少取
# 量子位 3 + The Decoder 3 + Solidot 2 + HN 2 = 10
SOURCE_QUOTAS = {
    "qbitai": 3,
    "thdecoder": 3,
    "solidot": 2,
    "hn": 2,
}

SOURCES = [
    {
        "id": "qbitai",
        "label": "量子位",
        "color": "#FF6B35",
        "type": "rss",
        "url": "https://www.qbitai.com/feed",
        "ai": True,
    },
    {
        "id": "solidot",
        "label": "Solidot",
        "color": "#1F6FEB",
        "type": "rss",
        "url": "https://www.solidot.org/index.rss",
    },
    {
        "id": "thdecoder",
        "label": "The Decoder",
        "color": "#9D4EDD",
        "type": "rss",
        "url": "https://the-decoder.com/feed/",
        "ai": True,
    },
    {
        "id": "hn",
        "label": "Hacker News",
        "color": "#FF6600",
        "type": "rss_hn",
        "url": "https://news.ycombinator.com/rss",
    },
]

PER_SOURCE = 2  # 默认每源 2 条（个别源用 SOURCE_QUOTAS 覆盖）
FETCH_TIMEOUT = 25

# ──── 抓取器 ──────────────────────────────────────────

def fetch_url(url, timeout=FETCH_TIMEOUT):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def fetch_rss(src, limit=PER_SOURCE):
    """RSS 抓取（量子位 / Solidot / The Decoder）"""
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
        if len(items) >= limit:
            break
    return items

def fetch_rss_hn(src, limit=PER_SOURCE):
    """Hacker News RSS（描述仅 "Comments" 链接，需自行用 OG description 抓取或留空）"""
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
        # HN 的 description 只有 "Comments" 链接，清洗后是空文本
        desc = ""
        if desc_el is not None and desc_el.text:
            cleaned = re.sub(r"<[^>]+>", " ", desc_el.text).strip()
            cleaned = re.sub(r"\s+", " ", cleaned)
            if cleaned and cleaned.lower() != "comments":
                desc = cleaned[:160]
        items.append({
            "source": src["id"],
            "label": src["label"],
            "color": src["color"],
            "title": title,
            "url": link,
            "subtitle": desc,  # HN 没 description，留空（后续 enrich_og 补）
        })
        if len(items) >= limit:
            break
    return items

def enrich_og_description(items):
    """对 subtitle 为空的条目用 Playwright 抓 OG description（P1-A DEC-015）"""
    need = [it for it in items if not it.get("subtitle")]
    if not need:
        return items
    print(f"  🪄 OG enrichment: {len(need)} 条待补")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
        )
        page = ctx.new_page()
        page.set_default_timeout(15000)
        for it in need:
            try:
                page.goto(it["url"], wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(1500)
                desc = page.evaluate("""() => {
                    const m1 = document.querySelector('meta[property="og:description"]');
                    const m2 = document.querySelector('meta[name="description"]');
                    return (m1 && m1.content) || (m2 && m2.content) || '';
                }""")
                if desc:
                    it["subtitle"] = re.sub(r"\s+", " ", desc).strip()[:160]
                    print(f"     ✅ {it['label']} | {it['title'][:40]}")
                else:
                    print(f"     ⚠️ {it['label']} | {it['title'][:40]} (no OG)")
            except Exception as ex:
                print(f"     ❌ {it['label']} | {str(ex)[:50]}")
        browser.close()
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
        quota = SOURCE_QUOTAS.get(src["id"], PER_SOURCE)
        print(f"📡 {src['label']:<6}（{quota} 条）", end=" ", flush=True)
        try:
            if src["type"] == "rss":
                items = fetch_rss(src, limit=quota)
            elif src["type"] == "rss_hn":
                items = fetch_rss_hn(src, limit=quota)
            elif src["type"] == "json_api":
                items = fetch_json_api(src)[:quota]
            elif src["type"] == "playwright_list_with_detail":
                items = fetch_playwright_list(src)[:quota]
            else:
                items = []
            print(f"✅ {len(items)} 条")
            all_items.extend(items)
            summary.append({"source": src["id"], "label": src["label"], "count": len(items)})
        except Exception as e:
            print(f"❌ {type(e).__name__}: {str(e)[:80]}")
            traceback.print_exc(limit=2)
            summary.append({"source": src["id"], "label": src["label"], "count": 0, "error": str(e)[:80]})
    
    # P1-A: 给 subtitle 为空的条目补 OG description（HN 专用）
    all_items = enrich_og_description(all_items)
    
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