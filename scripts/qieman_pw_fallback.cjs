// 且慢长赢调仓兜底抓取 (playwright 浏览器渲染)
// 背景: REST pmdj 接口 8/12-8/13 连续空 body, 按知识库 §9.2 兜底
const { chromium } = require('playwright-core');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  const saves = [];
  page.on('response', async (resp) => {
    const url = resp.url();
    if (/adjustments|nav-history|graphql|\/plan/.test(url)) {
      try {
        const ct = resp.headers()['content-type'] || '';
        if (ct.includes('json')) {
          const body = await resp.text();
          if (body && body.length > 200) {
            const name = url.includes('adjustments') ? 'adjustments'
              : url.includes('nav-history') ? 'nav-history'
              : url.includes('graphql') ? 'graphql' : 'plan';
            const f = `/tmp/qieman_pw_${name}_${Date.now()}.json`;
            fs.writeFileSync(f, body);
            saves.push({ name, url: url.slice(0, 140), size: body.length, file: f });
            console.log(`SAVED ${name} ${body.length} -> ${f}`);
          }
        }
      } catch (e) {}
    }
  });
  try {
    await page.goto('https://qieman.com/longwin', { waitUntil: 'domcontentloaded', timeout: 45000 });
  } catch (e) { console.log('goto err:', e.message); }
  // 滚动触发懒加载
  for (let i = 0; i < 5; i++) {
    await page.evaluate(() => window.scrollBy(0, 800));
    await page.waitForTimeout(1500);
  }
  await page.waitForTimeout(5000);
  await browser.close();
  console.log('TOTAL SAVED:', saves.length);
  if (!saves.length) console.log('NO JSON RESPONSES CAPTURED');
})();
