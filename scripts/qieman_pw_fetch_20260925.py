# -*- coding: utf-8 -*-
"""2026-09-25 盘中档：且慢 playwright 兜底抓取（REST pmdj 连续第 91 日空 body）
   - 打开 https://qieman.com/longwin ，拦截 response：
       /pmdj/v2/long-win/plan  -> /tmp/qieman_pw_plan_*.json
       nav-history             -> /tmp/qieman_pw_nav-history_*.json
       graphql                 -> /tmp/qieman_pw_graphql_*.json
   - 仅抓取，不做任何落库判断（判定在 qieman_ingest_20260925.py）
"""
import json, os, subprocess, sys, time, glob

NODE = '/Users/jieyang/.workbuddy/binaries/node/versions/22.22.2-3/bin/node'
WS = '/Users/jieyang/.workbuddy/binaries/node/workspace'

JS = r'''
const { chromium } = require('playwright-core');
(async () => {
  const browser = await chromium.launch({
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: true,
    args: ['--no-sandbox', '--disable-blink-features=AutomationControlled']
  });
  const ctx = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    viewport: { width: 1440, height: 900 }
  });
  const page = await ctx.newPage();
  const saved = [];
  let idx = { plan: 0, nav: 0, gql: 0, adj: 0 };
  page.on('response', async (resp) => {
    try {
      const u = resp.url();
      let tag = null;
      if (u.includes('/pmdj/v2/long-win/plan/adjustments')) tag = 'adj';
      else if (u.includes('/pmdj/v2/long-win/plan/nav-history')) tag = 'nav';
      else if (/\/pmdj\/v2\/long-win\/plan(\?|$)/.test(u)) tag = 'plan';
      else if (u.includes('/alfa/v1/graphql')) tag = 'gql';
      if (!tag) return;
      const body = await resp.text();
      if (!body || body.length < 5) return;
      idx[tag] += 1;
      const ts = Date.now();
      const fn = `/tmp/qieman_pw_${tag}_20260925_${ts}_${idx[tag]}.json`;
      require('fs').writeFileSync(fn, body);
      saved.push(`${tag} ${body.length}B -> ${fn}`);
    } catch (e) {}
  });
  await page.goto('https://qieman.com/longwin', { waitUntil: 'networkidle', timeout: 90000 });
  await page.waitForTimeout(6000);
  // 触发净值/调仓 tab
  try { await page.mouse.wheel(0, 2500); await page.waitForTimeout(2500); } catch(e){}
  try { await page.mouse.wheel(0, 2500); await page.waitForTimeout(2500); } catch(e){}
  saved.forEach(s => console.log(s));
  console.log('TOTAL=' + saved.length);
  await browser.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
'''

p = '/tmp/qieman_pw_fetch_20260925.cjs'
open(p, 'w', encoding='utf-8').write(JS)
env = dict(os.environ)
env['NODE_PATH'] = WS + '/node_modules'
r = subprocess.run([NODE, p], capture_output=True, text=True, env=env, timeout=180)
print(r.stdout[-4000:])
print('STDERR:', r.stderr[-2000:])
sys.exit(r.returncode)
