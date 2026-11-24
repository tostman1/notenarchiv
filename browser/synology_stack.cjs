// Actual NAS-profile containers through a synthetic private TLS proxy; no test settings.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {chromium} = require('playwright-core');

async function run(origin, ids) {
 const browser = await chromium.launch({channel: process.env.BROWSER_CHANNEL || 'chrome'});
 try {
  // Self-signed certificate exists only in disposable CI, not the installation guide.
  const context = await browser.newContext({ignoreHTTPSErrors:true, serviceWorkers:'block', acceptDownloads:true});
  const external=[], errors=[];
  await context.route('**/*', route => {
   if(new URL(route.request().url()).origin===origin)return route.continue();
   external.push(route.request().url());return route.abort();
  });
  const page=await context.newPage();page.on('pageerror', e=>errors.push(e.message));
  async function submit(button){
   const [response]=await Promise.all([page.waitForNavigation({waitUntil:'load'}),button.click()]);
   assert.notEqual(response.status(),500,'Synthetic browser submission returned HTTP 500');
  }
  async function download(label, count){
   const link=page.getByRole('link',{name:label,exact:true});
   for(let i=0;i<160 && await link.count()!==count;i++){await page.reload();await page.waitForTimeout(500);}
   assert.equal(await link.count(),count);
   for(const target of await link.all()){
    const [file]=await Promise.all([page.waitForEvent('download'),target.click()]);
    assert.equal(await file.failure(),null);
    const stream=await file.createReadStream(),chunks=[];for await(const chunk of stream)chunks.push(chunk);
    assert.equal(Buffer.concat(chunks).subarray(0,5).toString(),'%PDF-');
    const anonymous=await browser.newContext({ignoreHTTPSErrors:true});
    assert.equal((await anonymous.request.get(origin+await target.getAttribute('href'),{maxRedirects:0})).status(),302);
    await anonymous.close();
   }
  }
  await page.goto(origin);assert.equal(new URL(page.url()).pathname,'/login/');
  await page.getByLabel('Benutzername').fill('synthetic-archivist');await page.getByLabel('Passwort').fill(ids.password);
  await submit(page.getByRole('button',{name:'Anmelden'}));
  assert.match(await page.locator('body').innerText(),/Testversion – ausschließlich für Testdaten/);
  for(const key of ['ocr','enhancement','marchbook','printing','nas']){
   const feature=page.locator(`[data-feature="${key}"]`);
   assert.equal(await feature.locator('button').isDisabled(),true);assert.equal(await feature.locator('a').count(),0);
  }
  assert.equal((await page.request.get(`${origin}/diagnostics/`)).status(),404);
  for(const path of ['/ocr/','/printing/','/scan-enhancement/'])assert.equal((await page.request.post(origin+path)).status(),404);
  for(const resource of ['/static/css/base.css','/static/vendor/htmx/htmx.min.js','/static/archive/preview.mjs']){
   assert.equal((await page.request.get(origin+resource)).status(),200);
  }
  const cookies=await context.cookies();assert.ok(cookies.find(c=>c.name==='notenarchiv_sessionid'&&c.secure&&c.httpOnly));
  await page.goto(`${origin}/archive/index/`);
  await page.getByLabel('Auswahl indizieren',{exact:false}).check();
  await submit(page.getByRole('button',{name:'Indizieren',exact:true}));
  await page.goto(`${origin}/archive/review/`);
  const links=()=>page.getByRole('link',{name:'Version prüfen und zuordnen',exact:true});
  for(let i=0;i<120&&await links().count()!==6;i++){await page.reload();await page.waitForTimeout(500);}
  assert.equal(await links().count(),6);
  const urls=await links().evaluateAll(elements=>elements.map(el=>el.href));
  for(const url of urls){
   await page.goto(url);await page.locator('#pdf-preview[data-rendered="true"]').waitFor();
   const body=await page.locator('main > p').filter({hasText:'.pdf'}).first().innerText();
   const title=Object.keys(ids.arrangements).find(title=>body.includes(title));assert.ok(title);
   const part=body.includes('Posaune 1.pdf')?ids.parts[0]:ids.parts[1];
   await page.getByLabel('Arrangement / Ausgabe',{exact:false}).selectOption(ids.arrangements[title]);
   await page.getByLabel('Instrumentenvarianten',{exact:false}).selectOption(ids.instrument);
   await page.getByLabel('Musikalische Stimmen',{exact:false}).selectOption(part);
   await submit(page.getByRole('button',{name:'Zuordnung speichern'}));
   await page.locator('#pdf-preview[data-rendered="true"]').waitFor();
   const pages=Number(await page.locator('#pdf-count').innerText());
   for(let number=2;number<=pages;number++){
    await page.locator('#pdf-next').click();
    await page.waitForFunction(number=>document.querySelector('#pdf-page').value===String(number),number);
    await page.locator('#pdf-preview[data-rendered="true"]').waitFor();
   }
   assert.equal(await page.getByRole('button',{name:'Freigabe beauftragen'}).isDisabled(),true);
   await page.getByLabel('Ich habe alle Seiten',{exact:false}).check();
   await submit(page.getByRole('button',{name:'Visuelle Prüfung speichern'}));
   await page.getByLabel('Diese von mir visuell geprüfte',{exact:false}).check();
   await submit(page.getByRole('button',{name:'Freigabe beauftragen'}));
  }
  await page.goto(`${origin}/archive/review/`);
  for(let i=0;i<120&&await links().count();i++){await page.reload();await page.waitForTimeout(500);}
  assert.equal(await links().count(),0);
  await page.goto(`${origin}/projects/${ids.project}/participants/`);
  assert.equal(await page.locator('input[name="member"]:checked').count(),3);
  await submit(page.getByRole('button',{name:'Auswahl dieser Seite speichern'}));
  await page.reload();assert.equal(await page.locator('input[name="member"]:checked').count(),3);
  await page.goto(`${origin}/projects/${ids.project}/ensemble/`);
  await page.getByRole('link',{name:'Rolle hinzufügen'}).click();
  await page.getByLabel('Rollenkürzel').fill('Test');
  await page.getByLabel('Musikalische Rollenbezeichnung').fill('Synthetische Testrolle');
  await submit(page.getByRole('button',{name:'Ensemblezuordnung speichern'}));
  const first=page.locator(`[data-participant="${ids.people[0]}"]`);
  const role=await first.locator('select option').nth(1).getAttribute('value');
  await first.getByLabel('Musikalische Rolle').selectOption(role);
  await submit(first.getByRole('button',{name:'Teilnehmerrolle speichern'}));
  await page.getByRole('link',{name:'Mapping hinzufügen'}).click();
  await page.getByLabel('Musikalische Rolle').selectOption(role);
  await page.getByLabel('Spielbare Instrumentenvariante').selectOption(ids.instrument);
  await page.getByLabel('Spielbare Stimme',{exact:false}).selectOption(ids.parts[0]);
  await submit(page.getByRole('button',{name:'Ensemblezuordnung speichern'}));
  // Publication is asynchronous, but a successful queue action alone is not acceptance.
  await page.goto(`${origin}/projects/${ids.project}/matrix/`);
  const cell=()=>page.locator(`tr[data-position="${ids.positions[0]}"] td[data-participant="${ids.people[2]}"]`);
  for(let i=0;i<120&&!await cell().getByLabel('Spielbare Stimme und konkrete Ausgabe').count();i++){await page.reload();await page.waitForTimeout(500);}
  await page.waitForFunction(()=>!!window.htmx);
  const choice=cell().getByLabel('Spielbare Stimme und konkrete Ausgabe');
  const value=await choice.locator('option').filter({hasText:'Posaune 2'}).first().getAttribute('value');
  assert.ok(value);await choice.selectOption(value);
  const revision=Number(await page.locator('#matrix-panel').getAttribute('data-revision'));
  await cell().getByRole('button',{name:'Persönliche Ausgabe speichern'}).click();
  await page.waitForFunction(revision=>Number(document.querySelector('#matrix-panel').dataset.revision)===revision+1,revision);
  await page.reload();assert.match(await cell().innerText(),/Persönlicher Stück-Override/);
  assert.equal(await page.locator(`tr[data-position="${ids.positions[1]}"] :is(select,button,input,a)`).count(),0);
  for(const variant of ['READING','PRINT']){
   await page.goto(`${origin}/projects/${ids.project}/preflight/`);
   await page.getByLabel('Ausgabeart',{exact:true}).selectOption(variant);
   await submit(page.getByRole('button',{name:'Auswahl prüfen'}));
   assert.ok(await page.locator('input[name="acknowledgements"]').count()>0);
   await submit(page.getByRole('button',{name:'Persönliche Mappen verbindlich erstellen'}));
   assert.match(await page.getByRole('alert').innerText(),/fehlende Zuordnung/);
   for(const check of await page.locator('input[name="acknowledgements"]').all())await check.check();
   await submit(page.getByRole('button',{name:'Persönliche Mappen verbindlich erstellen'}));
   await page.getByRole('link',{name:'Ergebnis und Auftrag öffnen'}).click();
   await download(variant==='READING'?'Persönliche Lese-PDF herunterladen':'Druck-PDF herunterladen',3);
   if(variant==='PRINT'){
    await page.getByRole('link',{name:'Druck-PDF-Vorschau',exact:true}).first().click();
    await page.locator('#pdf-preview[data-rendered="true"]').waitFor();
   }
  }
  await page.goto(`${origin}/projects/${ids.project}/excerpts/`);
  for(const check of await page.locator('input[name="participants"]').all())await check.setChecked(await check.getAttribute('value')===ids.people[2]);
  for(const check of await page.locator('input[name="positions"]').all())await check.setChecked(await check.getAttribute('value')===ids.positions[0]);
  await submit(page.getByRole('button',{name:'Auswahl prüfen'}));
  await submit(page.getByRole('button',{name:'Gewählten Auszug verbindlich erstellen'}));
  await page.getByRole('link',{name:'Ergebnis und Auftrag öffnen'}).click();await download('Auszug herunterladen',1);
  await page.goto(`${origin}/exports/projects/${ids.project}/contents/`);
  await submit(page.getByRole('button',{name:'Inhaltsverzeichnis verbindlich erstellen'}));await download('Inhaltsverzeichnis herunterladen',1);
  await page.goto(`${origin}/exports/`);assert.ok(await page.locator('[data-artifact]').count()>=8);
  await page.goto(`${origin}/projects/${ids.project}/edit/`);
  await page.getByLabel('Projektname').fill('Synthetische Testmappe geändert');await submit(page.getByRole('button',{name:'Projekt speichern'}));
  await page.goto(`${origin}/exports/?kind=FULL&variant=READING`);assert.match(await page.locator('body').innerText(),/Veraltet/);
  await page.getByRole('link',{name:'Gezielt mit aktueller Auswahl neu erstellen'}).first().click();
  assert.equal(await page.locator('input[name="participants"]:checked').count(),1);
  await submit(page.getByRole('button',{name:'Auswahl prüfen'}));
  for(const check of await page.locator('input[name="acknowledgements"]').all())await check.check();
  await submit(page.getByRole('button',{name:'Persönliche Mappen verbindlich erstellen'}));
  await page.getByRole('link',{name:'Ergebnis und Auftrag öffnen'}).click();
  await download('Persönliche Lese-PDF herunterladen',1);
  assert.deepEqual(external,[]);assert.deepEqual(errors,[]);
 }finally{await browser.close();}
}
run(process.argv[2],JSON.parse(fs.readFileSync(process.argv[3],'utf8'))).catch(e=>{console.error(e);process.exitCode=1;});
