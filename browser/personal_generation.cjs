const assert=require('node:assert/strict');const {chromium}=require('playwright-core');
async function run(origin,project,person){
 const browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL||'chrome'});
 try{
  const context=await browser.newContext({serviceWorkers:'block',acceptDownloads:true}),errors=[];
  await context.route('**/*',route=>new URL(route.request().url()).origin===origin?route.continue():route.abort());
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  await page.goto(`${origin}/projects/${project}/preflight/`);
  await page.getByLabel('Benutzername').fill('synthetic-editions');await page.getByLabel('Passwort').fill('Synthetic-snapshot-135');
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Anmelden'}).click()]);
  for(const input of await page.locator('input[name="participants"]').all())await input.setChecked(await input.getAttribute('value')===person);
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Auswahl prüfen'}).click()]);
  const create=page.getByRole('button',{name:'Persönliche Mappen verbindlich erstellen'});
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),create.click()]);
  assert.match(await page.locator('[role="alert"]').innerText(),/fehlende Zuordnung/);
  for(const checkbox of await page.locator('input[name="acknowledgements"]').all())await checkbox.check();
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),create.click()]);
  await page.getByRole('link',{name:'Ergebnis und Auftrag öffnen'}).click();
  const link=page.getByRole('link',{name:'Persönliche Lese-PDF herunterladen'});
  for(let i=0;i<60&&!(await link.count());i++){await page.reload({waitUntil:'load'});await page.waitForTimeout(250);}
  assert.equal(await link.count(),1);assert.match(await page.locator('body').innerText(),/vollständig erstellt und geprüft/);
  const [download]=await Promise.all([page.waitForEvent('download'),link.click()]);
  assert.equal(await download.failure(),null);assert.equal(download.suggestedFilename(),'Lese-PDF.pdf');
  const stream=await download.createReadStream();let chunks=[];for await(const c of stream)chunks.push(c);
  assert.equal(Buffer.concat(chunks).subarray(0,5).toString(),'%PDF-');assert.deepEqual(errors,[]);
 }finally{await browser.close();}
}
run(new URL(process.argv[2]).origin,...process.argv.slice(3)).catch(e=>{console.error(e);process.exitCode=1;});
