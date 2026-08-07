import { viteBundler } from '@vuepress/bundler-vite'
import { defaultTheme } from '@vuepress/theme-default'
import { defineUserConfig } from 'vuepress'
import fs from 'node:fs'
import path from 'node:path'

/**
 * 扫描 docs/daily/ 下的日报文件，按月份分组生成侧边栏（时间倒序，最新在上）。
 *
 * 结构：
 *   每日日报
 *     ├ 全部日报（README 索引）
 *     ├ 每日日报-8月   ← 可折叠分组，点击展开/收起
 *     │    ├ 08-06
 *     │    └ ...
 *     └ 每日日报-7月
 *          └ ...
 *
 * 分组标题：默认 "每日日报-8月"；当日报跨多个年份时自动带年份 "每日日报-2026年8月"。
 * 说明：VuePress 会把 config 转译到 .temp 下执行，__dirname 不可靠，
 *       故从 process.cwd()（构建时 = 仓库根目录）推导 docs/daily 路径。
 */
function buildDailySidebar(): unknown[] {
  const candidates = [
    path.resolve(process.cwd(), 'docs/daily'),
    path.resolve(__dirname, '../daily'),
  ]
  const dailyDir = candidates.find((d) => fs.existsSync(d))
  if (!dailyDir) return []

  let files: string[] = []
  try {
    files = fs.readdirSync(dailyDir).filter((f) => /^\d{4}-\d{2}-\d{2}\.md$/.test(f))
  } catch {
    return []
  }
  if (files.length === 0) return []

  // 时间倒序：最新日期在最上面
  const sorted = files.sort().reverse()
  const multiYear = new Set(sorted.map((f) => f.slice(0, 4))).size > 1

  // 按 YYYY-MM 分组（组内保持倒序）
  const groups = new Map<string, string[]>()
  for (const f of sorted) {
    const ym = f.slice(0, 7)
    if (!groups.has(ym)) groups.set(ym, [])
    groups.get(ym)!.push(`/daily/${f}`)
  }

  const groupItems = Array.from(groups.entries())
    .sort((a, b) => (a[0] < b[0] ? 1 : -1)) // 月份倒序
    .map(([ym, links]) => {
      const [y, m] = ym.split('-')
      return {
        text: multiYear ? `每日日报-${y}年${Number(m)}月` : `每日日报-${Number(m)}月`,
        collapsible: true,
        children: links.map((link) => {
          const fname = link.replace('/daily/', '').replace('.md', '')
          return {
            text: `${fname.slice(5, 7)}-${fname.slice(8, 10)}`,
            link,
          }
        }),
      }
    })

  return [
    {
      text: '每日日报',
      children: ['/daily/README.md', ...groupItems],
    },
  ]
}

export default defineUserConfig({
  lang: 'zh-CN',
  title: 'WealthHub · 家庭理财日报',
  description: '家庭资产配置自动化投研平台（脱敏公开版）',
  base: '/WealthHub/',
  bundler: viteBundler(),
  theme: defaultTheme({
    logo: null,
    navbar: [
      { text: '首页', link: '/' },
      { text: '每日日报', link: '/daily/' },
      { text: '周报', link: '/weekly/' },
      { text: '关于', link: '/about.html' },
    ],
    sidebar: {
      '/daily/': buildDailySidebar(),
      '/weekly/': [
        {
          text: '周报',
          children: ['/weekly/README.md'],
        },
      ],
    },
    // 注意: 不配置 repo,避免导航栏出现 GitHub 链接暴露仓库(仓库含未脱敏持仓数据)
    // lastUpdated/contributors 关闭: 防止 git 插件从 remote 推断并注入仓库 URL 与提交信息
    lastUpdated: false,
    contributors: false,
    editLink: false,
  }),
})
