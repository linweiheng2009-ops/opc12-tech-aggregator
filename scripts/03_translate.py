#!/usr/bin/env python3
"""
OPC12 翻译 · MyMemory 免费 API 英→中
- 翻译 thdecoder / hn 源的 title 和 subtitle
- 输入：data/YYYY-MM-DD.json
- 输出：data/YYYY-MM-DD.json（同文件覆盖）

DEC-017 · 2026-08-16 恒哥选 C（Google Translate 免费接口）
实际实现：Google Translate 隐藏 API（translate.googleapis.com）已被官方封死，
返回 {"src":""} 空响应。降级到 MyMemory translated.net：
- 免费 5000 字符/天/IP（足够 10 条 × 200 字符 = 2000 字符/天）
- 不需要 API key
- 稳定可商用
"""
import json, os, sys, urllib.request, urllib.error, urllib.parse, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# MyMemory translated.net endpoint（免费，5000 字/天）
MM_URL = "https://api.mymemory.translated.net/get"

# 需要翻译的英文源
EN_SOURCES = {"thdecoder", "hn"}

def translate_one(text, source="en", target="zh-CN", retries=3):
    """MyMemory 单段翻译"""
    if not text or not text.strip():
        return text
    
    params = {
        "q": text,
        "langpair": f"{source}|{target}",
    }
    url = f"{MM_URL}?{urllib.parse.urlencode(params)}"
    
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 OPC12-TechAggregator/1.0",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                payload = json.loads(r.read())
                status = payload.get("responseStatus", 0)
                if status == 200:
                    translated = payload.get("responseData", {}).get("translatedText", "")
                    if translated:
                        return translated
                    else:
                        if attempt < retries - 1:
                            time.sleep(1)
                            continue
                        return None
                elif status == 403:  # quota exceeded
                    print(f"   ⚠️ MyMemory 配额超限（5000 字符/天）")
                    return None
                else:
                    if attempt < retries - 1:
                        time.sleep(1)
                        continue
                    detail = payload.get("responseDetails", "")
                    print(f"   ❌ MyMemory {status}: {detail[:120]}")
                    return None
        except urllib.error.HTTPError as e:
            if attempt < retries - 1:
                time.sleep(1.5 ** attempt)
                continue
            print(f"   ❌ HTTP {e.code}: {e.read().decode('utf-8', errors='replace')[:120]}")
            return None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1.5 ** attempt)
                continue
            print(f"   ❌ Error: {e}")
            return None
    return None

def translate_batch(texts, source="en", target="zh-CN"):
    """逐段翻译"""
    results = []
    for t in texts:
        translated = translate_one(t, source=source, target=target)
        results.append(translated if translated is not None else t)
    return results

def main():
    if len(sys.argv) > 1:
        date = sys.argv[1]
    else:
        from datetime import datetime
        date = datetime.now().strftime('%Y-%m-%d')
    
    today_file = DATA / f"{date}.json"
    if not today_file.exists():
        print(f"❌ {today_file} 不存在")
        sys.exit(1)
    
    payload = json.load(open(today_file))
    items = payload["items"]
    
    # 找出需要翻译的（英文源）
    en_items = []
    for it in items:
        if it["source"] in EN_SOURCES:
            en_items.append(it)
    
    if not en_items:
        print(f"✅ {date} 无英文条目，跳过翻译")
        return 0
    
    # 收集所有需要翻译的文本（title + subtitle）
    texts = []
    meta = []  # [(item_index, field_name)]
    for i, it in enumerate(items):
        if it["source"] in EN_SOURCES:
            texts.append(it["title"])
            meta.append((i, "title"))
            if it.get("subtitle"):
                texts.append(it["subtitle"])
                meta.append((i, "subtitle"))
    
    print(f"🌐 MyMemory 英→中：{len(en_items)} 条英文条目 ({len(texts)} 段)...")
    translated = translate_batch(texts)
    
    # 写回
    success = 0
    for k, txt in enumerate(translated):
        idx, field = meta[k]
        if txt and txt != texts[k]:
            items[idx][field] = txt
            success += 1
    
    payload["items"] = items
    today_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"✅ 翻译 {success}/{len(texts)} 段，写回 {today_file.name}")
    for it in en_items:
        print(f"   [{it['source']}] {it['title'][:80]}")
        if it.get('subtitle'):
            print(f"      └─ {it['subtitle'][:80]}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())