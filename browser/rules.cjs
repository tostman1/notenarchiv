const assert=require('node:assert/strict');const {chromium}=require('playwright-core');
async function check(origin,project,arr,desired,target,edition,position){
 const browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL||'chrome'});
 try{
 const ctx=await browser.newContext({serviceWorkers:'block'}),external=[];
 await ctx.route('**/*',r=>{if(new URL(r.request().url()).origin===origin)return r.continue();external.push(r.request().url());return r.abort();});
 const page=await ctx.newPage();
 async function submit(button){const [response]=await Promise.all([page.waitForNavigation({waitUntil:'load'}),button.click()]);assert.equal(response.status(),200);}
 await page.goto(origin+'/projects/replacement-rules/');await page.getByLabel('Benutzername').fill('synthetic-editions');await page.getByLabel('Passwort').fill('Synthetic-rules-135');await submit(page.getByRole('button',{name:'Anmelden'}));
 await page.getByRole('link',{name:'Ersatzregel hinzufügen'}).click();
 await page.getByLabel('Gewünschte spielbare Stimme').selectOption(desired);await page.getByLabel('Explizite Ersatzstimme').selectOption(target);await submit(page.getByRole('button',{name:'Regel speichern'}));
 await page.goto(`${origin}/projects/${project}/rules/replacements/new/`);await page.getByLabel('Gewünschte spielbare Stimme').selectOption(desired);await page.getByLabel('Explizite Ersatzstimme').selectOption(target);await page.getByLabel('Position (leer = Projektvorgabe)').selectOption(position);await submit(page.getByRole('button',{name:'Regel speichern'}));
 await page.getByRole('link',{name:'Ausgabenpräferenz setzen oder ändern'}).click();await page.getByLabel('Arrangement',{exact:false}).selectOption(arr);await page.getByLabel('Spielbare Stimme',{exact:false}).selectOption(desired);await page.getByLabel('Konkrete bestätigte Ausgabe').selectOption(edition);await submit(page.getByRole('button',{name:'Regel speichern'}));
 await page.getByRole('button',{name:'Projekt-Ausgabe ausdrücklich zurücksetzen'}).waitFor();await submit(page.getByRole('button',{name:'Projekt-Ausgabe ausdrücklich zurücksetzen'}));await page.reload();assert.match(await page.locator('body').innerText(),/Zurückgesetzt/);assert.deepEqual(external,[]);
 }finally{await browser.close();}
}
check(new URL(process.argv[2]).origin,...process.argv.slice(3)).catch(e=>{console.error(e);process.exitCode=1;});
