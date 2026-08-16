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

# AI/科技 术语词典
# DEC-017 P2：避免 LLM→法学硕士 这种字面错误
# 策略：
#   PRE_REPLACE 在翻译前把英文缩写展开（如 LLM → Large Language Model），
#   让 MyMemory 能识别 AI 语境
#   POST_REPLACE 在翻译后修正中文译法（如 "大语言模型" 标准化）
import re as _re

# 翻译前预处理：英文缩写 → 占位符（MyMemory 不会动占位符）
# 翻译后占位符还原成中文术语
PRE_REPLACE = [
    (r"\bLLMs?\b", "__LLM__"),       # 翻译后 → 大语言模型
    (r"\bGenAI\b", "__GenAI__"),     # 翻译后 → 生成式AI
    (r"\bAGI\b", "__AGI__"),         # 翻译后 → 通用人工智能
    (r"\bGPU(s)?\b", "__GPU__"),     # 翻译后 → GPU
    (r"\bAPIs?\b", "__API__"),       # 翻译后 → API
    (r"\bRLHF\b", "__RLHF__"),       # 翻译后 → 人类反馈强化学习
    (r"\bRAG\b", "__RAG__"),         # 翻译后 → 检索增强生成
    (r"\bVR\b", "__VR__"),
    (r"\bAR\b", "__AR__"),
    (r"\bIoT\b", "__IoT__"),
    (r"\bSaaS\b", "__SaaS__"),
    (r"\bNLP\b", "__NLP__"),
    (r"\bCV\b", "__CV__"),
    (r"\bML\b", "__ML__"),
    (r"\bDL\b", "__DL__"),
]

# 翻译后后处理：占位符还原 + 错误修正
# 容忍 MyMemory 可能在 __LLM__ 周围加空格（变成 "__ LLM __"）
# 不使用 \b（中文无单词边界）
POST_REPLACE = [
    # 占位符 → 中文术语（容忍空格）
    ("__LLM__", "大语言模型"),
    ("__ LLM __", "大语言模型"),
    ("__GenAI__", "生成式AI"),
    ("__AGI__", "通用人工智能"),
    ("__GPU__", "GPU"),
    ("__API__", "API"),
    ("__RLHF__", "RLHF"),
    ("__RAG__", "RAG"),
    ("__VR__", "VR"),
    ("__AR__", "AR"),
    ("__IoT__", "物联网"),
    ("__SaaS__", "SaaS"),
    ("__NLP__", "自然语言处理"),
    ("__CV__", "计算机视觉"),
    ("__ML__", "机器学习"),
    ("__DL__", "深度学习"),
    # 错误修正（纯字符串替换，不用正则 \b）
    ("法学硕士", "大语言模型"),
    ("理学硕士", "大语言模型"),
    ("人性人", "Anthropic"),
    ("Optima平台平台", "Optima"),
    ("Optima平台", "Optima"),
    ("人工分析推出了Optima", "Artificial Analysis 推出了Optima"),
]

# 翻译后后处理：中文译法标准化 + 品牌名本地化
TERM_DICT = [
    # 缩写 → 中文（先大写匹配，再小写匹配）
    (r"\bLLMs?\b", "大语言模型"),
    (r"\bLLM\b", "大语言模型"),
    (r"\bGenAI\b", "生成式AI"),
    (r"\bAGI\b", "通用人工智能"),
    (r"\bGPU(s)?\b", "显卡"),
    (r"\bAPI(s)?\b", "API"),
    (r"\bOpenAI\b", "OpenAI"),
    (r"\bAnthropic\b", "Anthropic"),
    (r"\bChatGPT\b", "ChatGPT"),
    (r"\bClaude\b", "Claude"),
    (r"\bGemini\b", "Gemini"),
    (r"\bMicrosoft\b", "微软"),
    (r"\bGoogle\b", "谷歌"),
    (r"\bMeta\b", "Meta"),
    (r"\bNvidia\b", "英伟达"),
    (r"\bAmazon\b", "亚马逊"),
    (r"\bApple\b", "苹果"),
    (r"\bTesla\b", "特斯拉"),
    (r"\bSpaceX\b", "SpaceX"),
    (r"\bAsus\b", "华硕"),
    (r"\bGitHub\b", "GitHub"),
    (r"\bLinux\b", "Linux"),
    (r"\bAndroid\b", "Android"),
    (r"\bAWS\b", "AWS"),
    (r"\bAzure\b", "Azure"),
    (r"\bDocker\b", "Docker"),
    (r"\bKubernetes\b", "Kubernetes"),
    (r"\bVR\b", "VR"),
    (r"\bAR\b", "AR"),
    (r"\bXR\b", "XR"),
    (r"\b5G\b", "5G"),
    (r"\bIoT\b", "物联网"),
    (r"\bSaaS\b", "SaaS"),
    (r"\bML\b", "机器学习"),
    (r"\bDL\b", "深度学习"),
    (r"\bNLP\b", "自然语言处理"),
    (r"\bCV\b", "计算机视觉"),
    (r"\bRLHF\b", "人类反馈强化学习"),
    (r"\bRAG\b", "检索增强生成"),
    (r"\btransformer\b", "Transformer架构"),
    (r"\bbenchmark(s|ing)?\b", "基准测试"),
    (r"\bstartup(s)?\b", "初创公司"),
    (r"\bfunding\b", "融资"),
    (r"\bacquisition\b", "收购"),
    (r"\bvaluation\b", "估值"),
    (r"\brelease(d|s)?\b", "发布"),
    (r"\blaunch(es|ed)?\b", "发布"),
    (r"\bopen[- ]source\b", "开源"),
    (r"\bcode\s*generation\b", "代码生成"),
    (r"\bbio[- ]weapons?\b", "生物武器"),
    (r"\bfilter(ing)?\b", "过滤"),
    (r"\binternal\b", "内部"),
    (r"\breport(s|ed)?\b", "报告"),
    (r"\bfiltering system\b", "过滤系统"),
    (r"\bsafety\b", "安全"),
    (r"\brisk(s)?\b", "风险"),
    (r"\bexposed?\b", "暴露"),
    (r"\bnearly a year\b", "近一年"),
    (r"\binactive\b", "停用"),
    (r"\bduring that time\b", "在此期间"),
    (r"\bphysics\b", "物理学"),
    (r"\bAsus\b", "华硕"),
    (r"\bpeak boost\b", "峰值增压"),
    (r"\beco range\b", "节能续航"),
    (r"\bapp control\b", "应用程序控制"),
    (r"\bfast charging\b", "快速充电"),
    (r"\briders?\b", "骑手"),
    (r"\bbike(s)?\b", "自行车"),
    (r"\bgrade\b", "年级"),
    (r"\bbeyond fifth grade\b", "超过五年级"),
    (r"\bnever sees\b", "从未见过"),
    (r"\bmaterial(s)?\b", "材料"),
    (r"\btransforms\b", "改造"),
    (r"\beasy install\b", "轻松安装"),
    (r"\bfor riders?\b", "面向骑手"),
    # 标题常用错误修正
    (r"人工分析推出了Optima", "Artificial Analysis推出了Optima平台"),  # MyMemory 把 "Artificial Analysis" 当品牌名错译
    (r"自行车助推器", "自行车动力增强器"),
]

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

def pre_expand(text):
    """翻译前：英文缩写 → 占位符（MyMemory 不会动占位符）"""
    for pattern, repl in PRE_REPLACE:
        text = _re.sub(pattern, repl, text)
    return text

def apply_term_dict(text):
    """翻译后：占位符还原 + 错误修正（纯字符串替换）"""
    for old, new in POST_REPLACE:
        text = text.replace(old, new)
    return text

def translate_batch(texts, source="en", target="zh-CN"):
    """逐段翻译 + 术语占位符前后处理"""
    results = []
    for t in texts:
        expanded = pre_expand(t)
        translated = translate_one(expanded, source=source, target=target)
        if translated is not None:
            translated = apply_term_dict(translated)
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
    
    # 写回：对所有英文条目跑一次 POST_REPLACE（不论翻译是否成功）
    # 这样可以修正已是中文的 JSON 里残留的错误译法（如“法学硕士”）
    success = 0
    for i, it in enumerate(items):
        if it["source"] in EN_SOURCES:
            for field in ("title", "subtitle"):
                txt = it.get(field, "") or ""
                if txt:
                    new = apply_term_dict(txt)
                    if new != txt:
                        it[field] = new
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