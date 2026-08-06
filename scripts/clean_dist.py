#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建后清理脚本: 移除 dist 产物中的隐私泄漏
================================================
问题: VuePress 内置 git 插件会把仓库 remote URL(github.com/yangzai360/WealthHub)
与提交作者邮箱注入到每个页面的 changelog/contributors 数据中,
即使配置了 repo/lastUpdated/contributors 关闭也无法完全阻止(rc.30 已知行为)。

本脚本在 vuepress build 之后运行, 把产物中的:
  - 仓库 URL  https://github.com/yangzai360/WealthHub  → https://github.com/private/redacted
  - 裸仓库路径 github.com/yangzai360                  → github.com/private
  - 用户主页   https://github.com/yangzai              → https://github.com/private (git 插件注入的 contributor url)
  - 用户名     "yangzai" (username/author/name 字段)   → "private"
  - 作者邮箱   yangzai360@icloud.com                   → redacted@example.com
全部替换为不可达占位, 保证网页上无法点击进入真实 GitHub 主页/仓库。

用法: python3 scripts/clean_dist.py [dist_dir]
"""
import os
import re
import sys

DIST = sys.argv[1] if len(sys.argv) > 1 else "docs/.vuepress/dist"

# 替换规则: (正则, 替换) — 注意顺序: 先长后短, 完整 URL 优先
RULES = [
    # 完整仓库 URL(含 /commits/xxx 等后缀会一起匹配到仓库段)
    (re.compile(r"https?://github\.com/yangzai360/WealthHub"), "https://github.com/private/redacted"),
    # 裸仓库路径(可能出现在无协议前缀的字符串中)
    (re.compile(r"github\.com/yangzai360"), "github.com/private"),
    # git 插件注入的 contributor 主页 URL(用户名主页, 负向前瞻避免误伤 yanzai360 形态)
    (re.compile(r"https?://github\.com/yangzai(?![a-zA-Z0-9_-])"), "https://github.com/private"),
    (re.compile(r"github\.com/yangzai(?![a-zA-Z0-9_-])"), "github.com/private"),
    # 用户名字段(git 插件 contributors/changelog 数据)
    (re.compile(r'"username":"yangzai"'), '"username":"private"'),
    (re.compile(r'"author":"yangzai"'), '"author":"private"'),
    (re.compile(r'"name":"yangzai"'), '"name":"private"'),
    # 提交作者邮箱
    (re.compile(r"yangzai360@icloud\.com"), "redacted@example.com"),
]

TEXT_EXTS = {".js", ".html", ".json", ".css", ".svg", ".xml", ".txt"}


def main() -> int:
    dist = os.path.abspath(DIST)
    if not os.path.isdir(dist):
        print(f"ERROR: {dist} 不存在")
        return 1

    replaced_files = 0
    total_replacements = 0
    for root, _dirs, files in os.walk(dist):
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext not in TEXT_EXTS:
                continue
            fp = os.path.join(root, name)
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue

            new_content = content
            count = 0
            for pat, repl in RULES:
                new_content, n = pat.subn(repl, new_content)
                count += n
            if count > 0:
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(new_content)
                replaced_files += 1
                total_replacements += count
                print(f"  ✂  {fp}: {count} 处替换")

    print(f"\n完成: {replaced_files} 个文件, {total_replacements} 处替换")

    # 最终验证
    leftovers = []
    for root, _dirs, files in os.walk(dist):
        for name in files:
            fp = os.path.join(root, name)
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            if re.search(r"github\.com/yangzai|yangzai360@icloud", content):
                leftovers.append(fp)
    if leftovers:
        print("⚠️  仍有残留:", leftovers)
        return 1
    print("✅ 验证通过: 产物中无仓库路径/个人邮箱残留")
    return 0


if __name__ == "__main__":
    sys.exit(main())
