const assert = require('node:assert/strict');
const {chromium} = require('playwright-core');

async function run(origin, edition) {
  const browser = await chromium.launch({channel: process.env.BROWSER_CHANNEL || 'chrome'});
  try {
    const context = await browser.newContext({serviceWorkers: 'block'});
    await context.route('**/*', route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const url = `${origin}/exports/content/${edition}/preference/`;
    await page.goto(url);
    await page.getByLabel('Benutzername').fill('synthetic-editions');
    await page.getByLabel('Passwort').fill('Synthetic-content-135');
    await Promise.all([page.waitForNavigation({waitUntil: 'load'}), page.getByRole('button', {name: 'Anmelden'}).click()]);
    const values = await page.locator('input[name="revision"]').evaluate(node => Object.fromEntries(new FormData(node.form)));
    const submit = action => page.evaluate(async ({url, values, action}) => {
      const response = await fetch(url, {method: 'POST', body: new URLSearchParams({...values, action})});
      return {status: response.status, url: response.url};
    }, {url, values, action});
    assert.deepEqual(await submit('set'), {status: 200, url});
    assert.equal((await submit('clear')).status, 409);
    await page.reload();
    await Promise.all([page.waitForNavigation({waitUntil: 'load'}), page.getByRole('button', {name: 'Präferenz für diese Stimme entfernen'}).click()]);
    assert.equal(page.url(), url);
    assert.deepEqual(errors, []);
  } finally {
    await browser.close();
  }
}
run(new URL(process.argv[2]).origin, process.argv[3]).catch(error => {console.error(error); process.exitCode = 1;});
