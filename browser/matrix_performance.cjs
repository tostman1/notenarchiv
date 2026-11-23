const assert = require('node:assert/strict');
const {chromium} = require('playwright-core');
async function run(origin, project, person, instrument) {
 const browser = await chromium.launch({channel: process.env.BROWSER_CHANNEL || 'chrome'});
 try {
  const context = await browser.newContext({serviceWorkers: 'block'}), external = [], errors = [];
  await context.route('**/*', route => {
   if (new URL(route.request().url()).origin === origin) return route.continue();
   external.push(route.request().url()); return route.abort();
  });
  const page = await context.newPage(); page.on('pageerror', e => errors.push(e.message));
  const url = `${origin}/projects/${project}/matrix/`;
  await page.goto(url);
  await page.getByLabel('Benutzername').fill('synthetic-editions');
  await page.getByLabel('Passwort').fill('Synthetic-matrix-performance-135');
  await Promise.all([page.waitForNavigation({waitUntil: 'load'}), page.getByRole('button', {name: 'Anmelden'}).click()]);
  await page.waitForFunction(() => !!window.htmx);
  assert.equal(await page.locator('#assignment-matrix tbody tr').count(), 25);
  assert.equal(await page.locator('#assignment-matrix thead th[data-participant]').count(), 10);
  await page.locator('.matrix-pagination input[name="rows"]').fill('4');
  await page.locator('.matrix-pagination input[name="people"]').fill('5');
  await page.getByRole('button', {name: 'Seite öffnen'}).click();
  await page.waitForFunction(() => document.querySelector('#assignment-matrix tbody th').textContent.trim().startsWith('76.'));
  assert.equal(await page.locator('#assignment-matrix tbody tr').count(), 25);
  const sticky = await page.locator('.matrix-scroll').evaluate(node => {
   node.scrollTop = 300; node.scrollLeft = 500;
   return [getComputedStyle(node.querySelector('thead th')).position, getComputedStyle(node.querySelector('tbody th')).position];
  });
  assert.deepEqual(sticky, ['sticky', 'sticky']);
  const filter = page.locator('.matrix-filters');
  await filter.locator('select[name="participant"]').selectOption(person);
  await filter.getByLabel('Instrumentenvariante').selectOption(instrument);
  await filter.getByLabel('Abweichungen').selectOption('personal');
  await page.getByRole('button', {name: 'Matrix filtern'}).click();
  await page.waitForFunction(() => document.querySelectorAll('#assignment-matrix tbody tr').length === 1);
  assert.equal(await page.locator('#assignment-matrix thead th[data-participant]').count(), 1);
  assert.match(await page.locator('#assignment-matrix tbody').innerText(), /Persönlicher Stück-Override/);
  assert.equal(await filter.locator('select[name="participant"]').inputValue(), person);
  await page.reload();
  assert.equal(await page.locator('#assignment-matrix tbody tr').count(), 1);
  assert.equal(await filter.locator('select[name="participant"]').inputValue(), person);
  // No-JS links retain filters; reload reconstructs the same filtered assignment.
  const nojs = await browser.newContext({javaScriptEnabled: false, storageState: await context.storageState()});
  const plain = await nojs.newPage();
  await plain.goto(url + `?participant=${person}&deviation=personal`);
  await plain.reload();
  assert.equal(await plain.locator('#assignment-matrix tbody tr').count(), 1);
  assert.match(await plain.getByRole('link', {name: 'Weitere Positionen'}).getAttribute('href'), /deviation=personal/);
  await nojs.close();
  assert.deepEqual(external, []); assert.deepEqual(errors, []);
 } finally { await browser.close(); }
}
run(new URL(process.argv[2]).origin, ...process.argv.slice(3)).catch(error => {console.error(error); process.exitCode = 1;});
