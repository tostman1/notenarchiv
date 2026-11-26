const assert = require('node:assert/strict');
const {chromium} = require('playwright-core');

async function run(origin, membership, work) {
  const browser = await chromium.launch({channel: process.env.BROWSER_CHANNEL || 'chrome'});
  try {
    const context = await browser.newContext({serviceWorkers: 'block'});
    await context.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const url = `${origin}/catalog/corrections/membership/${membership}/`;
    await page.goto(url);
    await page.getByLabel('Benutzername').fill('synthetic-correction-browser');
    await page.getByLabel('Passwort').fill('Synthetic-content-135');
    await Promise.all([page.waitForNavigation({waitUntil: 'load'}), page.getByRole('button', {name: 'Anmelden'}).click()]);
    const values = await page.locator('input[name="revision"]').evaluate(node => Object.fromEntries(new FormData(node.form)));
    const submit = () => page.evaluate(async ({url, values, work}) => {
      const response = await fetch(url, {method: 'POST', body: new URLSearchParams({...values, action: 'replace', reason: 'Synthetic wrong work', work, position: '0'})});
      return {status: response.status, url: response.url};
    }, {url, values, work});
    const replacement = await submit();
    assert.equal(replacement.status, 200);
    assert.notEqual(replacement.url, url);
    assert.equal((await submit()).status, 409);
    await page.goto(replacement.url);
    await page.getByLabel('Aktion').selectOption('withdraw');
    await page.getByLabel('Begründung').fill('Synthetic withdrawal');
    await Promise.all([page.waitForNavigation({waitUntil: 'load'}), page.getByRole('button', {name: 'Korrektur ausdrücklich speichern'}).click()]);
    await page.getByText('Diese Zuordnung wurde bereits zurückgenommen.', {exact: false}).waitFor();
    assert.deepEqual(errors, []);
  } finally { await browser.close(); }
}
run(new URL(process.argv[2]).origin, process.argv[3], process.argv[4]).catch(error => {console.error(error); process.exitCode = 1;});
