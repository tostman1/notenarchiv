const assert=require('node:assert/strict');const {chromium}=require('playwright-core');
async function run(origin,project,file){
 const browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL||'chrome'});
 try{
  const context=await browser.newContext({serviceWorkers:'block',acceptDownloads:true});
  await context.route('**/*',route=>new URL(route.request().url()).origin===origin?route.continue():route.abort());
  const page=await context.newPage();await page.goto(`${origin}/exports/?project=${project}`);
  await page.getByLabel('Benutzername').fill('synthetic-editions');await page.getByLabel('Passwort').fill('Synthetic-library-135');
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Anmelden'}).click()]);
  assert.equal(await page.locator('[data-artifact]').count(),2);assert.match(await page.locator('body').innerText(),/Historisch exakt reproduzierbar/);
  for(const input of await page.locator('input[name="artifacts"]').all())await input.check();
  const [zip]=await Promise.all([page.waitForEvent('download'),page.getByRole('button',{name:'Gewählte vollständige PDFs als ZIP herunterladen'}).click()]);
  assert.equal(await zip.failure(),null);assert.equal(zip.suggestedFilename(),'Notenausgaben.zip');
  await page.getByRole('link',{name:'Gezielt mit aktueller Auswahl neu erstellen'}).first().click();
  assert.equal(await page.locator('input[name="participants"]:checked').count(),1);
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Auswahl prüfen'}).click()]);
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Persönliche Mappen verbindlich erstellen'}).click()]);
  await page.getByRole('link',{name:'Ergebnis und Auftrag öffnen'}).click();
  let link=page.getByRole('link',{name:'Persönliche Lese-PDF herunterladen',exact:true});
  for(let i=0;i<100&&!(await link.count());i++){await page.reload({waitUntil:'load'});await page.waitForTimeout(250);}
  assert.equal(await link.count(),1);
  await page.goto(`${origin}/exports/archive/generate/`);await page.locator(`input[name="files"][value="${file}"]`).check();
  await page.getByLabel('PDF-Ausgabeart').selectOption('READING');
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Archiv-Auswahl prüfen'}).click()]);
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Gewählte Archiv-PDF verbindlich erstellen'}).click()]);
  link=page.getByRole('link',{name:'Persönliche Lese-PDF herunterladen',exact:true});
  for(let i=0;i<100&&!(await link.count());i++){await page.reload({waitUntil:'load'});await page.waitForTimeout(250);}
  const [download]=await Promise.all([page.waitForEvent('download'),link.click()]);assert.equal(await download.failure(),null);
  await page.goto(`${origin}/exports/?kind=ARCHIVE_NOTES`);assert.match(await page.locator('body').innerText(),/Einzelnoten/);
 }finally{await browser.close();}
}
run(new URL(process.argv[2]).origin,...process.argv.slice(3)).catch(e=>{console.error(e);process.exitCode=1;});
