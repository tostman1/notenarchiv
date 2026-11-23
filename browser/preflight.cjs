const assert = require('node:assert/strict');
const {chromium} = require('playwright-core');
async function run(origin, project, missing, ambiguous, corrupt, position) {
 const browser = await chromium.launch({channel: process.env.BROWSER_CHANNEL || 'chrome'});
 try {
  const context = await browser.newContext({serviceWorkers:'block'}), external=[], errors=[];
  await context.route('**/*', route => {
   if(new URL(route.request().url()).origin===origin) return route.continue();
   external.push(route.request().url()); return route.abort();
  });
  const page = await context.newPage(); page.on('pageerror', error => errors.push(error.message));
  const url = `${origin}/projects/${project}/preflight/`;
  await page.goto(url); await page.getByLabel('Benutzername').fill('synthetic-editions');
  await page.getByLabel('Passwort').fill('Synthetic-preflight-135');
  await Promise.all([page.waitForNavigation({waitUntil:'load'}), page.getByRole('button',{name:'Anmelden'}).click()]);
  const select = async person => {
   await page.goto(url);
   for(const input of await page.locator('input[name="participants"]').all()) await input.setChecked(await input.getAttribute('value')===person);
   for(const input of await page.locator('input[name="positions"]').all()) await input.setChecked(await input.getAttribute('value')===position);
   await Promise.all([page.waitForNavigation({waitUntil:'load'}), page.getByRole('button',{name:'Auswahl prüfen'}).click()]);
  };
  await select(ambiguous);
  assert.match(await page.locator('.preflight-cell').innerText(), /Mehrere Ausgaben/);
  assert.equal(await page.getByRole('button',{name:'Prüfergebnis und Platzhalter bestätigen'}).isDisabled(),true);
  await select(corrupt);
  assert.match(await page.locator('.preflight-cell').innerText(), /Hash stimmt nicht/);
  assert.equal(await page.getByRole('button',{name:'Prüfergebnis und Platzhalter bestätigen'}).isDisabled(),true);
  await select(missing);
  assert.match(await page.locator('.preflight-cell').innerText(), /Noten fehlen/);
  await Promise.all([page.waitForNavigation({waitUntil:'load'}), page.getByRole('button',{name:'Prüfergebnis und Platzhalter bestätigen'}).click()]);
  await page.getByRole('alert').filter({hasText:'Jede fehlende Zuordnung'}).waitFor();
  await page.locator('input[name="acknowledgements"]').check();
  await Promise.all([page.waitForNavigation({waitUntil:'load'}), page.getByRole('button',{name:'Prüfergebnis und Platzhalter bestätigen'}).click()]);
  await page.getByRole('status').filter({hasText:'Fehlende Noten ausdrücklich bestätigt'}).waitFor();
  assert.match(await page.locator('body').innerText(), /noch kein Generierungsauftrag/);
  assert.deepEqual(errors,[]); assert.deepEqual(external,[]);
 } finally {await browser.close();}
}
run(new URL(process.argv[2]).origin,...process.argv.slice(3)).catch(error=>{console.error(error);process.exitCode=1;});
