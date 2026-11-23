const assert=require('node:assert/strict');const {chromium}=require('playwright-core');
async function check(origin,project,person,part,file,first,second,reserve){
 const browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL||'chrome'});
 try{
  const context=await browser.newContext({serviceWorkers:'block'}),external=[],errors=[];
  await context.route('**/*',route=>{if(new URL(route.request().url()).origin===origin)return route.continue();external.push(route.request().url());return route.abort();});
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  const url=`${origin}/projects/${project}/matrix/`;
  await page.goto(url);await page.getByLabel('Benutzername').fill('synthetic-editions');await page.getByLabel('Passwort').fill('Synthetic-matrix-batch-135');
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Anmelden'}).click()]);
  await page.waitForFunction(()=>!!window.htmx);
  const stale=await context.newPage();await stale.goto(url);await stale.waitForFunction(()=>!!window.htmx);
  const cell=(target,slot)=>target.locator(`tr[data-position="${slot}"] td[data-participant="${person}"]`);
  const header=()=>page.locator(`thead th[data-participant="${person}"]`);
  await header().getByLabel('Mehrfachziel: Stimme und Notation').selectOption(part);
  await cell(page,first).getByLabel('Für Mehrfachaktion auswählen').check();
  await cell(page,second).getByLabel('Für Mehrfachaktion auswählen').check();
  const selectFile=async(target,slot)=>{
   const select=cell(target,slot).getByLabel('Konkrete Ausgabe für Mehrfachänderung');
   await select.selectOption(await select.locator('option').filter({hasText:file}).getAttribute('value'));
  };
  await selectFile(page,first);
  await header().getByRole('button',{name:'Ausgewählte Zellen speichern'}).click();
  await page.getByRole('alert').filter({hasText:'Mindestens eine konkrete Ausgabe fehlt'}).waitFor();
  assert.equal(await page.locator('#matrix-panel').getAttribute('data-revision'),'1');
  // Error re-render intentionally requires deliberate fresh selection, never retry.
  await header().getByLabel('Mehrfachziel: Stimme und Notation').selectOption(part);
  for(const slot of [first,second]){await cell(page,slot).getByLabel('Für Mehrfachaktion auswählen').check();await selectFile(page,slot);}
  await header().getByRole('button',{name:'Ausgewählte Zellen speichern'}).click();
  await page.waitForFunction(()=>document.querySelector('#matrix-panel').dataset.revision==='2');
  for(const slot of [first,second]){assert.match(await cell(page,slot).innerText(),/Persönlicher Stück-Override/);assert.match(await cell(page,slot).innerText(),new RegExp(file));}
  await stale.locator(`thead th[data-participant="${person}"]`).getByLabel('Mehrfachziel: Stimme und Notation').selectOption(part);
  await cell(stale,first).getByLabel('Für Mehrfachaktion auswählen').check();await selectFile(stale,first);
  await stale.locator(`thead th[data-participant="${person}"]`).getByRole('button',{name:'Ausgewählte Zellen speichern'}).click();
  await stale.getByRole('alert').filter({hasText:'Projekt oder Archiv geändert'}).waitFor();
  await cell(page,first).getByRole('button',{name:'Diesen Override zurücksetzen'}).click();
  await page.waitForFunction(()=>document.querySelector('#matrix-panel').dataset.revision==='3');
  await page.reload();assert.match(await cell(page,first).innerText(),/Gespeicherter Projektdefault/);
  assert.doesNotMatch(await cell(page,first).innerText(),/Persönlicher Stück-Override/);
  assert.match(await cell(page,second).innerText(),/Persönlicher Stück-Override/);
  assert.equal(await page.locator(`tr[data-position="${reserve}"] :is(select,button,input,a)`).count(),0);
  assert.equal(await page.locator('#assignment-matrix tbody tr').count(),3);
  const nojs=await browser.newContext({javaScriptEnabled:false,storageState:await context.storageState(),serviceWorkers:'block'});
  const plain=await nojs.newPage();await plain.goto(url);
  await cell(plain,second).getByLabel('Für Mehrfachaktion auswählen').check();
  const plainHead=plain.locator(`thead th[data-participant="${person}"]`);
  await Promise.all([plain.waitForNavigation({waitUntil:'load'}),plainHead.getByRole('button',{name:'Ausgewählte Overrides zurücksetzen'}).click()]);
  assert.equal(await plain.locator('#matrix-panel').getAttribute('data-revision'),'4');
  assert.doesNotMatch(await cell(plain,second).innerText(),/Persönlicher Stück-Override/);
  await nojs.close();
  assert.deepEqual(external,[]);assert.deepEqual(errors,[]);
 }finally{await browser.close();}
}
check(new URL(process.argv[2]).origin,...process.argv.slice(3)).catch(e=>{console.error(e);process.exitCode=1;});
