#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_site.py — WealthHub 站点构建脚本（脱敏公开版）

职责:
1. 扫描 reports/daily/*.md 与 reports/weekly/*.md
2. 脱敏转换(隐藏绝对金额/个股名称/账户持有人, 保留百分比/指数行情/情绪/策略)
3. 输出到 docs/daily/、docs/weekly/(带 frontmatter)
4. 从 data/processed/ 生成图表数据 docs/.vuepress/public/data/charts.json
5. 更新 docs/daily/README.md 日报索引 与 docs/README.md 首页
"""
import csv
import json
import os
import re
import shutil
import glob
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS = os.path.join(REPO, "reports")
DOCS = os.path.join(REPO, "docs")
PROC = os.path.join(REPO, "data", "processed")
CHARTS_JSON = os.path.join(DOCS, ".vuepress", "public", "data", "charts.json")

# ---------- 脱敏规则 ----------
# 1. 账户/持有人 → 匿名
TOKEN_MAP = [
    ("sean-alipay-fund", "基金账户A"),
    ("jasy-alipay-fund", "基金账户B"),
    ("stock-brokerage", "股票账户"),
    ("Sean", "持有人"),
    ("Jasy", "持有人"),
    ("广联达", "个股A(软件)"),
    ("通威股份", "个股B(光伏)"),
    ("通威", "个股B(光伏)"),
]
# 2. 受保护章节(保留公开数字: 指数点位/行情/新闻/情绪/策略占比)
PROTECTED_SECTIONS = ("行情", "新闻", "情绪", "指数", "历史影响", "策略建议", "核心结论")
# 3. 金额模式: 只打码绝对金额, 保留百分比(%结尾)与裸点位
#    - "约X万" / "X元" / "X,XXX.XX"(千分位金额) 三类
AMOUNT_PATTERNS = [
    re.compile(r"约\s*[\d,]+(?:\.\d+)?\s*万"),
    re.compile(r"[\d,]+(?:\.\d+)?\s*元"),
    re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?"),
]

def mask_amounts(text: str) -> str:
    for pat in AMOUNT_PATTERNS:
        text = pat.sub("***", text)
    return text

def desensitize_md(content: str) -> str:
    # 保护 markdown 链接中的 URL, 防止金额脱敏规则误伤(如 URL 含数字/千分位形态)
    # 处理顺序: 保护 URL → 脱敏(TOKEN_MAP + 金额) → 最后还原 URL
    url_placeholders = {}
    def protect_url(m):
        key = f"__URL{len(url_placeholders)}__"
        url_placeholders[key] = m.group(2)
        return f"[{m.group(1)}]({key})"
    content = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", protect_url, content)

    for src, dst in TOKEN_MAP:
        content = content.replace(src, dst)
    # 按行处理: 受保护章节保留数字, 其他章节金额脱敏
    out_lines = []
    in_protected = False
    for line in content.split("\n"):
        if line.startswith("#"):
            in_protected = any(s in line for s in PROTECTED_SECTIONS)
        if not in_protected:
            line = mask_amounts(line)
        out_lines.append(line)
    content = "\n".join(out_lines)

    # 还原链接 URL(在脱敏完成后)
    for key, url in url_placeholders.items():
        content = content.replace(f"({key})", f"({url})")
    return content

def frontmatter(title: str, date: str, tags: list) -> str:
    tags_str = ", ".join(f'"{t}"' for t in tags)
    return f"---\ntitle: {title}\ndate: {date}\ntags: [{tags_str}]\n---\n\n"

# ---------- 日报转换 ----------
def convert_daily():
    daily_src = os.path.join(REPORTS, "daily")
    daily_dst = os.path.join(DOCS, "daily")
    os.makedirs(daily_dst, exist_ok=True)
    # 清理旧文件(只留 README)
    for f in glob.glob(os.path.join(daily_dst, "*.md")):
        if os.path.basename(f) != "README.md":
            os.remove(f)
    entries = []
    for src in sorted(glob.glob(os.path.join(daily_src, "*.md"))):
        fname = os.path.basename(src)          # 2026-08-06.md
        date = fname.replace(".md", "")
        with open(src, encoding="utf-8-sig") as f:
            content = f.read()
        masked = desensitize_md(content)
        # 提取各档位章节标题用于 tags
        sections = re.findall(r"^##\s+(.+)", masked, re.M)
        tags = []
        for s in sections:
            if "盘前" in s: tags.append("盘前分析")
            elif "盘中" in s: tags.append("盘中调仓")
            elif "盘后" in s: tags.append("盘后复盘")
        if not tags:
            tags = ["日报"]
        # 加上"上一日/下一日"导航
        dst_path = os.path.join(daily_dst, fname)
        # 正文前注入右侧目录组件(段落导航显示在页面右侧, 宽屏固定/窄屏浮动)
        out = frontmatter(f"WealthHub 日报 {date}", date, tags) + "<RightToc />\n\n" + masked
        with open(dst_path, "w", encoding="utf-8") as f:
            f.write(out)
        # 提取核心结论摘要
        m = re.search(r"\*\*一句话结论\*\*:\s*(.+)", masked)
        summary = m.group(1).strip() if m else ""
        entries.append((date, summary, f"/daily/{fname}"))
    # 写日报索引 README
    lines = ["# 每日日报\n", "按日期归档，最新在上。完整日报见「正文」，本页为索引。\n", ""]
    for date, summary, link in sorted(entries, reverse=True):
        lines.append(f"- **[{date}]({link})** — {summary[:80]}{'…' if len(summary) > 80 else ''}")
    with open(os.path.join(daily_dst, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return entries

# ---------- 周报转换 ----------
def convert_weekly():
    weekly_src = os.path.join(REPORTS, "weekly")
    weekly_dst = os.path.join(DOCS, "weekly")
    os.makedirs(weekly_dst, exist_ok=True)
    if not os.path.isdir(weekly_src):
        return []
    for f in glob.glob(os.path.join(weekly_dst, "*.md")):
        if os.path.basename(f) != "README.md":
            os.remove(f)
    entries = []
    for src in sorted(glob.glob(os.path.join(weekly_src, "*.md"))):
        fname = os.path.basename(src)
        date = fname.replace(".md", "")
        with open(src, encoding="utf-8-sig") as f:
            content = f.read()
        masked = desensitize_md(content)
        dst_path = os.path.join(weekly_dst, fname)
        out = frontmatter(f"WealthHub 周报 {date}", date, ["周报"]) + masked
        with open(dst_path, "w", encoding="utf-8") as f:
            f.write(out)
        entries.append((date, f"/weekly/{fname}"))
    lines = ["# 周报\n", "按周归档。\n", ""]
    for date, link in sorted(entries, reverse=True):
        lines.append(f"- **[周报 {date}]({link})**")
    with open(os.path.join(weekly_dst, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return entries

# ---------- 图表数据 ----------
def track_of(name: str) -> str:
    TRACKS = [
        ("全球医疗", "美股标普医药"), ("海外中国互联", "恒生科技"), ("恒生科技", "恒生科技"),
        ("恒指科技", "恒生科技"), ("中概", "恒生科技"), ("消费", "大消费"), ("养老", "大消费"),
        ("文体", "大消费"), ("医药", "A股医药"), ("医疗", "A股医药"), ("健康", "A股医药"),
    ]
    for k, v in TRACKS:
        if k in name:
            return v
    return "其他/宽基"

def build_charts():
    charts = {}
    # 1) 赛道分布(从 holdings 快照, 仅百分比, 不泄露金额)
    track_amt = {}
    for csv_path in glob.glob(os.path.join(REPO, "holdings", "*", "snapshot-*.csv")):
        with open(csv_path, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                amt = float(row["amount"]) if row.get("amount", "").strip() else 0
                track_amt[track_of(row["name"])] = track_amt.get(track_of(row["name"]), 0) + amt
    total = sum(track_amt.values())
    charts["track_dist"] = [
        {"name": k, "value": round(v / total * 100, 2)} for k, v in sorted(track_amt.items(), key=lambda x: -x[1])
    ] if total else []
    # 2) 指数行情
    idx_csv = os.path.join(PROC, "history", "indices.csv")
    indices = []
    if os.path.exists(idx_csv):
        with open(idx_csv, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                try:
                    indices.append({
                        "name": row["name"], "date": row["date"],
                        "close": float(row["close"]), "pct": float(row["pct_change"]),
                    })
                except (ValueError, KeyError):
                    continue
    charts["indices"] = indices
    # 3) ETF 盘中行情
    etf_csv = os.path.join(PROC, "history", "etf_intraday.csv")
    etfs = []
    if os.path.exists(etf_csv):
        with open(etf_csv, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                try:
                    etfs.append({"name": row["name"], "pct": float(row["pct"])})
                except (ValueError, KeyError):
                    continue
    charts["etf_quotes"] = etfs
    # 4) 场外基金净值
    fund_csv = os.path.join(PROC, "history", "fund_nav.csv")
    funds = []
    if os.path.exists(fund_csv):
        with open(fund_csv, encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                try:
                    funds.append({"name": row["name"], "nav": float(row["nav"]), "pct": float(row["pct"])})
                except (ValueError, KeyError):
                    continue
    charts["fund_navs"] = funds
    # 5) 情绪分析(赛道 → 强度均值)
    events = {}
    for ej in glob.glob(os.path.join(PROC, "events", "*.json")):
        with open(ej, encoding="utf-8") as f:
            for ev in json.load(f):
                t = ev.get("track", "其他")
                s = ev.get("strength")
                if isinstance(s, (int, float)):
                    events.setdefault(t, []).append(float(s))
    charts["sentiment"] = [
        {"name": k, "value": round(sum(v) / len(v), 1)} for k, v in sorted(events.items(), key=lambda x: -sum(x[1]) / len(x[1]))
    ] if events else []
    os.makedirs(os.path.dirname(CHARTS_JSON), exist_ok=True)
    with open(CHARTS_JSON, "w", encoding="utf-8") as f:
        json.dump(charts, f, ensure_ascii=False, indent=2)
    return charts

# ---------- 首页 ----------
def build_home(entries, charts):
    latest = entries[0] if entries else None
    latest_link = f"[{latest[0]} 日报](/daily/{latest[0]}.md)" if latest else "暂无"
    latest_sum = latest[1] if latest else ""
    content = f"""# WealthHub · 家庭理财日报

> 家庭资产配置自动化投研平台（**脱敏公开版**：不展示具体金额 / 个股 / 盈亏）。
> 完整内部分析见本地仓库 `reports/`，本站为公开摘要与决策看板。

## 📊 最新日报

**{latest_link}**

{latest_sum}

## 🥧 决策看板

<DashboardCharts />

## 📅 日报归档

- 全部日报 → [每日日报索引](/daily/)
- 周报 → [周报归档](/weekly/)

---
*数据来源: AKShare 公开行情 + 新闻情绪分析 · 由 WealthHub 自动化投研 Agent 生成*
"""
    with open(os.path.join(DOCS, "README.md"), "w", encoding="utf-8") as f:
        f.write(content)

def main():
    entries = convert_daily()
    convert_weekly()
    charts = build_charts()
    build_home(entries, charts)
    print(f"✅ docs 构建完成: {len(entries)} 份日报, {len(charts.get('indices', []))} 条指数, {len(charts.get('track_dist', []))} 个赛道")
    print(f"   图表数据 → {os.path.relpath(CHARTS_JSON, REPO)}")

if __name__ == "__main__":
    main()
