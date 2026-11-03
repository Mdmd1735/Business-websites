// Usage: node playbook/qa.js <slug> [outdir]   (serves docs/ on :8765, screenshots 1440 + 390, checks overflow & errors)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const slug = process.argv[2], out = process.argv[3] || '.';
(async () => {
  const srv = spawn('python3', ['-m', 'http.server', '8765'], { cwd: path.join(__dirname, '..', 'docs'), stdio: 'ignore' });
  await new Promise(r => setTimeout(r, 800));
  const b = await chromium.launch(); let fail = 0;
  for (const [name, vp] of [['desktop', { width: 1440, height: 900 }], ['mobile', { width: 390, height: 844 }]]) {
    const p = await b.newPage({ viewport: vp }); const errs = [];
    p.on('pageerror', e => errs.push(e.message));
    p.on('console', m => m.type() === 'error' && !/net::ERR|Failed to load/.test(m.text()) && errs.push(m.text()));
    await p.goto(`http://localhost:8765/${slug}/`, { waitUntil: 'domcontentloaded' });
    await p.waitForTimeout(1500);
    await p.screenshot({ path: `${out}/${slug}-${name}-hero.png` });
    // scroll through so lazy images + scroll animations fire, then force any reveal classes
    await p.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += innerHeight * .6) { scrollTo(0, y); await new Promise(r => setTimeout(r, 120)); } scrollTo(0, 0); });
    await p.evaluate(() => document.querySelectorAll('.reveal,.rv').forEach(e => e.classList.add('is-in', 'on')));
    await p.waitForTimeout(1500);
    await p.screenshot({ path: `${out}/${slug}-${name}-full.png`, fullPage: true });
    const res = await p.evaluate(() => ({
      overflowX: document.documentElement.scrollWidth - innerWidth,
      noindex: !!document.querySelector('meta[name=robots][content*=noindex]'),
      imgsNoAlt: [...document.images].filter(i => !i.hasAttribute('alt')).length,
      smallTargets: [...document.querySelectorAll('a,button')].filter(e => { const r = e.getBoundingClientRect(); return r.width && r.height && r.height < 40 && getComputedStyle(e).display !== 'inline'; }).length,
    }));
    const ok = res.overflowX <= 0 && !errs.length && res.noindex && !res.imgsNoAlt;
    if (!ok) fail = 1;
    console.log(`${ok ? 'PASS' : 'FAIL'} ${name}`, JSON.stringify(res), errs.length ? errs : '');
  }
  await b.close(); srv.kill(); process.exit(fail);
})();
