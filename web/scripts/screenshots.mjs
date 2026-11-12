// Visual review: screenshots of every view at desktop and phone widths, light and dark.
// Usage: npm run build && npx vite preview --port 4173 &  then  node scripts/screenshots.mjs [filter]
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const BASE = process.env.URL ?? 'http://localhost:4173/';
const OUT = process.env.OUT ?? 'screenshots';
const only = process.argv[2];
mkdirSync(OUT, { recursive: true });

const sizes = { desktop: { width: 1440, height: 900 }, mobile: { width: 375, height: 812 } };
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

const scenarios = {
  court: async (page) => {
    await page.goto(BASE + '#court');
    await page.waitForSelector('.scene svg');
    for (let i = 0; i < 24; i++) await page.getByRole('button', { name: /^Step/ }).click();
    await wait(2200);
  },
  'court-end': async (page) => {
    await page.goto(BASE + '#court');
    await page.waitForSelector('.scene svg');
    await page.getByRole('button', { name: /To verdict/ }).click();
    await wait(600);
  },
  gallery: async (page) => {
    await page.goto(BASE + '#gallery');
    await page.waitForSelector('.seats');
    await page.getByRole('button', { name: /1 % noise/ }).click();
    await page.selectOption('select[aria-label="Generations per second"]', '60');
    await wait(5200);
    await page.getByRole('button', { name: 'Pause' }).click();
    await page.locator('.seat').nth(37).click();
    await wait(500);
  },
  labs: async (page) => {
    await page.goto(BASE + '#labs');
    await page.waitForSelector('.pi');
    await page.getByRole('button', { name: 'Run the sweep' }).click();
    await page.waitForSelector('text=Dots: one per run', { timeout: 60000 });
    await wait(400);
  },
  'court-m2': async (page) => {
    await page.goto(BASE + '#court?m=2');
    await page.waitForSelector('.scene svg');
    for (let i = 0; i < 30; i++) await page.getByRole('button', { name: /^Step/ }).click();
    await page.getByRole('button', { name: 'Edit the 18 bits' }).first().click();
    await wait(2200);
  },
  'gallery-m2': async (page) => {
    await page.goto(BASE + '#gallery?m=2');
    await page.waitForSelector('.seats');
    await page.getByRole('button', { name: /1 % noise/ }).click();
    await page.selectOption('select[aria-label="Generations per second"]', '60');
    await wait(7000);
    await page.getByRole('button', { name: 'Pause' }).click();
    await page.locator('.seat').nth(12).click();
    await wait(500);
  },
  'labs-m2': async (page) => {
    await page.goto(BASE + '#labs?m=2');
    await page.waitForSelector('.pi');
    await page.getByRole('button', { name: 'Test every mutant' }).click();
    await page.waitForSelector('text=no mutant can invade', { timeout: 120000 });
    await wait(400);
  },
};

const browser = await chromium.launch(process.env.CHROME ? { executablePath: process.env.CHROME } : {});
for (const [name, run] of Object.entries(scenarios)) {
  if (only && !name.startsWith(only)) continue;
  for (const [size, viewport] of Object.entries(sizes)) {
    for (const scheme of ['light', 'dark']) {
      const ctx = await browser.newContext({ viewport, colorScheme: scheme, deviceScaleFactor: size === 'mobile' ? 2 : 1 });
      const page = await ctx.newPage();
      const errors = [];
      page.on('pageerror', (e) => errors.push(e.message));
      page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
      await run(page);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      await page.screenshot({ path: `${OUT}/${name}-${size}-${scheme}.png`, fullPage: true });
      console.log(`${name}-${size}-${scheme}`, overflow > 0 ? `HORIZONTAL OVERFLOW ${overflow}px` : 'ok', errors.length ? errors : '');
      await ctx.close();
    }
  }
}
await browser.close();
