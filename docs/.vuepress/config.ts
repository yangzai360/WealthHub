import { viteBundler } from '@vuepress/bundler-vite'
import { defaultTheme } from '@vuepress/theme-default'
import { defineUserConfig } from 'vuepress'

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
      '/daily/': [
        {
          text: '每日日报',
          children: [
            '/daily/README.md',
            // 日报文件由 build_site.py 自动生成并注入到此处
          ],
        },
      ],
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
