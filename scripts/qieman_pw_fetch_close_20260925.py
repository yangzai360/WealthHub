# -*- coding: utf-8 -*-
"""2026-09-25 盘后档：且慢 playwright 兜底抓取（REST pmdj 连续第 92 日空 body）
   - 打开 https://qieman.com/longwin ，拦截 response：
       /pmdj/v2/long-win/plan             -> /tmp/qieman_pwc_plan_<TODAY>_*.json
       .../plan/nav-history               -> /tmp/qieman_pwc_nav_<TODAY>_*.json
       .../plan/adjustments               -> /tmp/qieman_pwc_adj_<TODAY>_*.json
   - 仅抓取，不做落库判断（判定在 qieman_ingest_close_<TODAY>.py）
"""
import os, subprocess, sys

NODE = '/Users/jieyang/.workbuddy/binaries/node/versions/22.22.2-3/bin/node'
WS = '/Users/jieyang/.workbuddy/binaries/node/workspace'
TAG = '20260925c'

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
      const fn = `/tmp/qieman_pwc_${tag}_TAGX_${ts}_${idx[tag]}.json`.replace('TAGX', 'TAGV');
      require('fs').writeFileSync(fn, body);
      saved.push(`${tag} ${body.length}B -> ${fn}`);
    } catch (e) {}
  });
  await page.goto('https://qieman.com/longwin', { waitUntil: 'networkidle', timeout: 90000 });
  await page.waitForTimeout(7000);
  try { await page.mouse.wheel(0, 2500); await page.waitForTimeout(2500); } catch(e){}
  try { await page.mouse.wheel(0, 2500); await page.waitForTimeout(2500); } catch(e){}
  try { await page.mouse.wheel(0, 2500); await page.waitForTimeout(2500); } catch(e){}
  saved.forEach(s => console.log(s));
  console.log('TOTAL=' + saved.length);
  await browser.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
'''.replace('TAGV', TAG)

p = f'/tmp/qieman_pw_fetch_close_{TAG}.cjs'
open(p, 'w', encoding='utf-8').write(JS)
env = dict(os.environ)
env['NODE_PATH'] = WS + '/node_modules'
r = subprocess.run([NODE, p], capture_output=True, text=True, env=env, timeout=240)
print(r.stdout[-4000:])
print('STDERR:', r.stderr[-1500:])
sys.exit(r.returncode)
