const assert=require('node:assert/strict');const {chromium}=require('playwright-core');
async function check(origin,project,position,person,file,assignment,defaultPart,reserve){
 const browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL||'chrome'});
 try{
  const context=await browser.newContext({serviceWorkers:'block'}),external=[],errors=[];
  await context.route('**/*',route=>{if(new URL(route.request().url()).origin===origin)return route.continue();external.push(route.request().url());return route.abort();});
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  const url=`${origin}/projects/${project}/matrix/`;
  await page.goto(url);await page.getByLabel('Benutzername').fill('synthetic-editions');await page.getByLabel('Passwort').fill('Synthetic-matrix-edit-135');
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Anmelden'}).click()]);
  await page.waitForFunction(()=>!!window.htmx);
  const stale=await context.newPage();await stale.goto(url);await stale.waitForFunction(()=>!!window.htmx);
  const cell=()=>page.locator(`tr[data-position="${position}"] td[data-participant="${person}"]`);
  const select=cell().getByLabel('Spielbare Stimme und konkrete Ausgabe');
  const token=await select.locator('option').filter({hasText:file}).getAttribute('value');
  await select.selectOption(token);await cell().getByRole('button',{name:'Persönliche Ausgabe speichern'}).click();
  await page.waitForFunction(()=>document.querySelector('#matrix-panel').dataset.revision==='2');
  assert.match(await cell().innerText(),/Persönlicher Stück-Override/);assert.match(await cell().innerText(),new RegExp(file));
  const staleCell=stale.locator(`tr[data-position="${position}"] td[data-participant="${person}"]`);
  await staleCell.getByLabel('Spielbare Stimme und konkrete Ausgabe').selectOption(token);
  await staleCell.getByRole('button',{name:'Persönliche Ausgabe speichern'}).click();
  await stale.getByRole('alert').filter({hasText:'Projekt oder Archiv geändert'}).waitFor();
  const header=page.locator(`thead th[data-participant="${person}"]`);
  await header.getByLabel('Gespeicherte Projektstimme').selectOption(defaultPart);await header.getByRole('button',{name:'Projektdefault speichern'}).click();
  await page.waitForFunction(()=>document.querySelector('#matrix-panel').dataset.revision==='3');
  assert.match(await cell().innerText(),/Persönlicher Stück-Override/);
  await page.reload();assert.match(await cell().innerText(),new RegExp(file));
  assert.equal(await page.locator(`tr[data-position="${reserve}"] :is(select,button,input,a)`).count(),0);
  assert.equal(await page.locator('#assignment-matrix tbody tr').count(),3);
  assert.deepEqual(external,[]);assert.deepEqual(errors,[]);
 }finally{await browser.close();}
}
check(new URL(process.argv[2]).origin,...process.argv.slice(3)).catch(e=>{console.error(e);process.exitCode=1;});
