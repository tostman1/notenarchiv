const assert=require('node:assert/strict');const {chromium}=require('playwright-core');
async function run(origin,project,person,position){
 const browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL||'chrome'});
 try{
  const context=await browser.newContext({serviceWorkers:'block',acceptDownloads:true}),errors=[];
  await context.route('**/*',route=>new URL(route.request().url()).origin===origin?route.continue():route.abort());
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  await page.goto(`${origin}/projects/${project}/excerpts/`);
  await page.getByLabel('Benutzername').fill('synthetic-editions');await page.getByLabel('Passwort').fill('Synthetic-snapshot-135');
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Anmelden'}).click()]);
  for(const input of await page.locator('input[name="participants"]').all())await input.setChecked(await input.getAttribute('value')===person);
  for(const input of await page.locator('input[name="positions"]').all())await input.setChecked(await input.getAttribute('value')===position);
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Auswahl prüfen'}).click()]);
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Gewählten Auszug verbindlich erstellen'}).click()]);
  await page.getByRole('link',{name:'Ergebnis und Auftrag öffnen'}).click();
  async function download(label,filename){
   const link=page.getByRole('link',{name:label,exact:true});
   for(let i=0;i<100&&!(await link.count());i++){await page.reload({waitUntil:'load'});await page.waitForTimeout(250);}
   assert.equal(await link.count(),1);const [file]=await Promise.all([page.waitForEvent('download'),link.click()]);
   assert.equal(await file.failure(),null);assert.equal(file.suggestedFilename(),filename);
   const stream=await file.createReadStream();let chunks=[];for await(const c of stream)chunks.push(c);
   assert.equal(Buffer.concat(chunks).subarray(0,5).toString(),'%PDF-');
  }
  await download('Auszug herunterladen','Auszug.pdf');
  await page.getByRole('link',{name:'Historische Einzelstimmen exakt nachdrucken',exact:true}).click();
  await page.locator(`input[name="participants"][value="${person}"]`).check();
  await page.locator(`input[name="positions"][value="${position}"]`).check();
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Historische Auswahl prüfen'}).click()]);
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Exakten historischen Auszug erstellen'}).click()]);
  await download('Auszug herunterladen','Auszug.pdf');
  await page.goto(`${origin}/exports/projects/${project}/contents/`);
  assert.equal(await page.locator('input[name="participants"]').count(),0);
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Inhaltsverzeichnis verbindlich erstellen'}).click()]);
  await download('Inhaltsverzeichnis herunterladen','Inhaltsverzeichnis.pdf');assert.deepEqual(errors,[]);
 }finally{await browser.close();}
}
run(new URL(process.argv[2]).origin,...process.argv.slice(3)).catch(e=>{console.error(e);process.exitCode=1;});
