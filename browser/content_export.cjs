const assert = require('node:assert/strict');
const {chromium} = require('playwright-core');

async function run(origin, edition) {
  const browser = await chromium.launch({channel: process.env.BROWSER_CHANNEL || 'chrome'});
  try {
    const context = await browser.newContext({serviceWorkers: 'block'});
    await context.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
    const page = await context.newPage(), errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const url = `${origin}/exports/content/generate/`;
    await page.goto(url);
    await page.getByLabel('Benutzername').fill('synthetic-editions');
    await page.getByLabel('Passwort').fill('Synthetic-content-135');
    await Promise.all([page.waitForNavigation({waitUntil: 'load'}), page.getByRole('button', {name: 'Anmelden'}).click()]);
    await page.locator(`input[name="editions"][value="${edition}"]`).check();
    await page.getByLabel('PDF-Ausgabeart').selectOption('READING');
    await Promise.all([page.waitForNavigation({waitUntil: 'load'}), page.getByRole('button', {name: 'Inhaltsauswahl prüfen'}).click()]);
    assert.equal(await page.locator('a', {hasText: 'Originalkontext'}).count(), 2);
    const payload = await page.locator('input[name="token"]').evaluate(node => Object.fromEntries(new FormData(node.form)));
    const submit = values => page.evaluate(async ({url, values}) => {
      const response = await fetch(url, {method: 'POST', body: new URLSearchParams({...values, action: 'authorize'})});
      return {status: response.status, url: response.url};
    }, {url, values});
    assert.equal((await submit({...payload, token: 'invalid'})).status, 409);
    const first = await submit(payload);
    assert.equal(first.status, 200);
    assert.notEqual(first.url, url);
    assert.deepEqual(await submit(payload), first);
    assert.deepEqual(errors, []);
  } finally {
    await browser.close();
  }
}
run(new URL(process.argv[2]).origin, process.argv[3]).catch(error => {console.error(error); process.exitCode = 1;});
