const assert = require('node:assert/strict');
const {chromium} = require('playwright-core');
async function check(origin, project, first, second, variant1, variant2, part1, part2, position) {
 const browser = await chromium.launch({channel: process.env.BROWSER_CHANNEL || 'chrome'});
 try {
  const ctx = await browser.newContext({serviceWorkers:'block'}), external = [], errors = [];
  await ctx.route('**/*', route => {if (new URL(route.request().url()).origin === origin) return route.continue(); external.push(route.request().url()); return route.abort();});
  const page = await ctx.newPage(); page.on('pageerror', e => errors.push(e.message));
  const url = `${origin}/projects/${project}/ensemble/`;
  await page.goto(url);
  await page.getByLabel('Benutzername').fill('ensemble-browser'); await page.getByLabel('Passwort').fill('Synthetic-ensemble-135');
  async function submit(button) {const [response] = await Promise.all([page.waitForNavigation({waitUntil:'load'}), button.click()]); assert.equal(response.status(),200);}
  await submit(page.getByRole('button',{name:'Anmelden'}));
  await page.getByRole('link',{name:'Rolle hinzufügen'}).click();
  await page.getByLabel('Rollenkürzel').fill('3'); await page.getByLabel('Musikalische Rollenbezeichnung').fill('Synthetic role');
  await submit(page.getByRole('button',{name:'Ensemblezuordnung speichern'}));
  const role = await page.locator(`[data-participant="${first}"] select`).locator('option').nth(1).getAttribute('value');
  for (const person of [first, second]) {
   const row = page.locator(`[data-participant="${person}"]`);
   await row.getByLabel('Musikalische Rolle').selectOption(role); await submit(row.getByRole('button',{name:'Teilnehmerrolle speichern'}));
  }
  assert.match(await page.locator('body').innerText(), /Mapping fehlt/);
  async function mapping(variant, part, pos='') {
   await page.goto(url+'mappings/new/');
   await page.getByLabel('Musikalische Rolle').selectOption(role);
   await page.getByLabel('Spielbare Instrumentenvariante').selectOption(variant);
   await page.getByLabel('Spielbare Stimme',{exact:false}).selectOption(part);
   if (pos) await page.getByLabel('Position (leer = Projektvorgabe)').selectOption(pos);
   await submit(page.getByRole('button',{name:'Ensemblezuordnung speichern'}));
  }
  await page.goto(url+'mappings/new/');
  await page.getByLabel('Musikalische Rolle').selectOption(role);
  await page.getByLabel('Spielbare Instrumentenvariante').selectOption(variant1);
  await page.getByLabel('Spielbare Stimme',{exact:false}).selectOption(part2);
  const [invalid] = await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Ensemblezuordnung speichern'}).click()]);
  assert.equal(invalid.status(),400); assert.match(await page.locator('body').innerText(), /Stimme passt nicht/);
  await mapping(variant1,part1); await mapping(variant2,part2); await mapping(variant1,part1,position);
  await page.goto(url+`?position=${position}`);
  assert.match(await page.locator(`[data-participant="${first}"]`).innerText(),/Positionsausnahme/);
  assert.match(await page.locator(`[data-participant="${second}"]`).innerText(),/Projektvorgabe/);
  const exception = page.locator('li').filter({hasText:'Positionsausnahme'}).filter({has:page.getByRole('button',{name:'Mapping ausdrücklich zurücksetzen'})});
  await submit(exception.getByRole('button',{name:'Mapping ausdrücklich zurücksetzen'}));
  await page.reload(); assert.match(await page.locator(`[data-participant="${first}"]`).innerText(), /Projektvorgabe/);
  assert.deepEqual(external,[]); assert.deepEqual(errors,[]);
 } finally {await browser.close();}
}
check(new URL(process.argv[2]).origin,...process.argv.slice(3)).catch(e=>{console.error(e);process.exitCode=1;});
