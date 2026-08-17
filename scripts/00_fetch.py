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
import time

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
        "type": "hn_api",
        # Algolia HN Search API：按时间抓 story，过滤过去 48h，按 score 排序后再筛 top
        "url": "https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage=100",
    },
]

PER_SOURCE = 2  # 默认每源 2 条（个别源用 SOURCE_QUOTAS 覆盖）
FETCH_TIMEOUT = 25

# ──── 抓取器 ──────────────────────────────────────────

def fetch_url(url, timeout=FETCH_TIMEOUT, retries=3):
    """GET 请求 + 指数退避重试（处理 GitHub Actions 容器偶发 SSL / 超时）"""
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
            last_err = e
            if attempt < retries:
                wait = 2 ** attempt  # 2 / 4 / 8 秒
                print(f"     ⚠️ fetch 失败 (attempt {attempt}/{retries}): {type(e).__name__} {str(e)[:50]} · {wait}s 后重试", flush=True)
                time.sleep(wait)
            else:
                print(f"     ❌ fetch 最终失败 ({retries} 次): {type(e).__name__} {str(e)[:80]}", flush=True)
    raise last_err

def fetch_rss(src, limit=PER_SOURCE):
    """RSS 抓取（量子位 / Solidot / The Decoder）"""
    xml_text = fetch_url(src["url"])
    root = ET.fromstring(xml_text)
    items = []
    # P2 热度：仅取过去 48h（2026-08-17 恒哥要求"收集的数据要有热度"）
    cutoff_48h = int(time.time()) - 48 * 3600
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
            desc = re.sub(r"\s+", " ", desc)[:400]  # 放宽到 400 字（之前 160 太少）
        if not title or not link:
            continue
        # P2 热度过滤：跳过 48h 之前的旧资讯
        pub_date_el = item.find("pubDate")
        if pub_date_el is not None and pub_date_el.text:
            try:
                from email.utils import parsedate_to_datetime
                pub_dt = parsedate_to_datetime(pub_date_el.text)
                pub_ts = int(pub_dt.timestamp())
                if pub_ts < cutoff_48h:
                    continue  # 太旧，跳过
            except Exception:
                pass  # 解析失败不拦
        items.append({
            "source": src["id"],
            "label": src["label"],
            "color": src["color"],
            "title": title,
            "url": link,
            "subtitle": desc,
            "score": None,  # RSS 无热度信号
            "comments": None,
        })
        if len(items) >= limit:
            break
    return items

def fetch_rss_hn(src, limit=PER_SOURCE):
    """Hacker News: Algolia API（取真实 points/comments，按热度排序）

    源：https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage=100
    - 返回过去 48h 所有 stories
    - 我们按 points 排序、取 top N（带 points >= MIN_POINTS 门槛）
    - URL 优先用 story_url（真实文章），Ask HN / Show HN fallback 到 HN item 页
    - P2 热度：2026-08-17 恒哥要求"收集的数据要有热度"
    """
    MIN_POINTS = 20  # 门槛：20 points 以上的才是热门
    raw = fetch_url(src["url"], timeout=20)
    payload = json.loads(raw)
    hits = payload.get("hits", [])
    # 过滤过去 48h
    cutoff = int(time.time()) - 48 * 3600
    recent = [h for h in hits if h.get("created_at_i", 0) >= cutoff]
    # 按 points 排序
    recent.sort(key=lambda h: (h.get("points", 0), h.get("num_comments", 0)), reverse=True)
    # 门槛过滤
    hot = [h for h in recent if h.get("points", 0) >= MIN_POINTS][:limit]
    items = []
    for h in hot:
        title = (h.get("title") or "").strip()
        url = h.get("url") or h.get("story_text") or ""
        if not url or not title:
            continue
        # Ask HN / Show HN 没外链，用 HN item 页
        if h.get("_tags") and "ask_hn" in h.get("_tags", []) and not h.get("url"):
            url = f"https://news.ycombinator.com/item?id={h['objectID']}"
        elif h.get("_tags") and "show_hn" in h.get("_tags", []) and not h.get("url"):
            url = f"https://news.ycombinator.com/item?id={h['objectID']}"
        items.append({
            "source": src["id"],
            "label": src["label"],
            "color": src["color"],
            "title": title,
            "url": url,
            "subtitle": "",  # HN 没 description，留空（后续 enrich_og 补）
            "score": h.get("points", 0),
            "comments": h.get("num_comments", 0),
        })
    print(f"  [hn] 热榜 {len(items)}/{len(recent)}（门槛 ≥ {MIN_POINTS} points）")
    return items
    return items

def enrich_summary(items, min_len=100, max_len=400):
    """对 subtitle 太短（<100 字）的条目抓 article 详情，提炼更长的概要（P1-C 2026-08-17 恒哥要求）

    优先级：OG description → first 3 paragraphs (article/post/main/p fallback)
    跳过 PDF（浏览器下载而非渲染，无法抓正文）→ 标记为 "PDF 全文 · 点击查看"
    防 footer 噪声：跳过"本站"、"ICP"、"版权所有"等明显是 footer 的文本
    """
    need = []
    for it in items:
        sub_len = len(it.get("subtitle") or "")
        url = it.get("url") or ""
        if sub_len >= min_len:
            continue
        if not url:
            continue
        # PDF 链接：标记但不抓详情（浏览器会下载而非渲染）
        if url.lower().endswith(".pdf"):
            if not it.get("subtitle"):
                it["subtitle"] = "📄 PDF 全文 · 点击查看"
            print(f"     📄 {it['label']} | {it['title'][:30]} (PDF 跳过详情)")
            continue
        need.append(it)
    if not need:
        print(f"  📖 概要补全：跳过（所有条目 ≥ {min_len} 字）")
        return items
    print(f"  📖 概要补全：{len(need)} 条待抓详情 (目标 {min_len}~{max_len} 字)")

    summary_js = """() => {
        const sels = [
            'article p',
            '.article-body p',
            '.post-body p',
            '.entry-content p',
            '.content p',
            'main p',
            'p'
        ];
        for (const sel of sels) {
            const els = Array.from(document.querySelectorAll(sel));
            const texts = els.map(p => (p.innerText || '').trim()).filter(t => t.length > 40);
            if (texts.length >= 1) {
                return texts.slice(0, 3).join('\\n\\n');
            }
        }
        return '';
    }"""

    # Footer / 噪声关键词（出现这些词说明是 footer 而非正文，不采用）
    noise_keywords = ["本站提到的所有注册商标", "ICP证", "ICP备案", "版权所有", "评论属于其发表者所有", "登录 注册"]

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
                # 1. 优先 OG description
                desc = page.evaluate("""() => {
                    const m1 = document.querySelector('meta[property="og:description"]');
                    const m2 = document.querySelector('meta[name="description"]');
                    return (m1 && m1.content) || (m2 && m2.content) || '';
                }""")
                # 2. fallback: first 3 paragraphs
                if not desc or len(desc) < min_len:
                    paras = page.evaluate(summary_js)
                    if paras:
                        desc = paras
                if desc:
                    desc = re.sub(r"\s+", " ", desc).strip()[:max_len]
                    # 防 footer：含明显噪声关键词就不采用（保留 RSS 原始描述）
                    is_noise = any(kw in desc for kw in noise_keywords)
                    old_len = len(it.get("subtitle") or "")
                    if is_noise:
                        print(f"     🚫 {it['label']} | {it['title'][:30]} (检测到 footer，保留 RSS 原始)")
                    elif len(desc) > old_len:
                        it["subtitle"] = desc
                        print(f"     ✅ {it['label']} | {it['title'][:30]} → {len(desc)} 字 (↑{len(desc)-old_len})")
                    else:
                        print(f"     ⏭ {it['label']} | {it['title'][:30]} (无提升)")
                else:
                    print(f"     ⚠️ {it['label']} | {it['title'][:30]} (无内容)")
            except Exception as ex:
                print(f"     ❌ {it['label']} | {str(ex)[:50]}")
        browser.close()
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
            elif src["type"] in ("rss_hn", "hn_api"):
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
    # 容错：OG enrichment 失败不影响主流程（items 已收集完毕，只是 subtitle 留空）
    try:
        # P1-C (2026-08-17 恒哥要求概要详细点)：抓 article 详情补概要
        # 容错：enrich_summary 整体失败不影响主流程（items 已收集，subtitle 保留 RSS 描述）
        try:
            all_items = enrich_summary(all_items, min_len=100, max_len=400)
        except Exception as e:
            print(f"⚠️  enrich_summary 整体失败（保留 RSS 描述）: {type(e).__name__}: {str(e)[:80]}")
            traceback.print_exc(limit=1)
        # P1-A: 给 subtitle 为空的条目补 OG description（HN 专用）
        # 容错：OG enrichment 失败不影响主流程（items 已收集完毕，只是 subtitle 留空）
        try:
            all_items = enrich_og_description(all_items)
        except Exception as e:
            print(f"⚠️  OG enrichment 整体失败（items 已收集，subtitle 留空）: {type(e).__name__}: {str(e)[:80]}")
            traceback.print_exc(limit=1)
    except Exception as e:
        print(f"⚠️  OG enrichment 整体失败（items 已收集，subtitle 留空）: {type(e).__name__}: {str(e)[:80]}")
        traceback.print_exc(limit=1)
    
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