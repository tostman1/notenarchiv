const assert=require('node:assert/strict');const {chromium}=require('playwright-core');
async function check(origin,project,first,reserve,third){
 const browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL||'chrome'});
 try{
 const ctx=await browser.newContext({serviceWorkers:'block'}),external=[];
 await ctx.route('**/*',route=>{if(new URL(route.request().url()).origin===origin)return route.continue();external.push(route.request().url());return route.abort();});
 const page=await ctx.newPage(),url=`${origin}/projects/${project}/pieces/`;
 async function submit(button){
  const revision=Number(await page.locator('input[name="expected_revision"]').first().inputValue());
  const [response]=await Promise.all([
   page.waitForResponse(response=>response.request().isNavigationRequest() && response.request().method()==='GET'
    && new URL(response.url()).pathname===new URL(url).pathname),button.click()]);
  assert.equal(response.status(),200);
  await page.waitForFunction(revision=>Number(document.querySelector('input[name="expected_revision"]')?.value)===revision+1,revision);
  await page.waitForLoadState('load');
 }
 await page.goto(url);await page.getByLabel('Benutzername').fill('pieces-browser');await page.getByLabel('Passwort').fill('Synthetic-pieces-135');await page.getByRole('button',{name:'Anmelden'}).click();await page.waitForLoadState('load');
 const rows=()=>page.locator('#piece-list > li[data-position]');
 assert.equal(await rows().count(),3);
 await page.locator(`[data-position="${third}"]`).dragTo(page.locator(`[data-position="${first}"]`));
 assert.equal(await rows().first().getAttribute('data-position'),third);
 assert.deepEqual(await page.locator('.piece-number').allTextContents(),['1.','2.','3.']);
 await submit(page.getByRole('button',{name:'Vorschau-Reihenfolge speichern'}));await page.reload();
 assert.equal(await rows().first().getAttribute('data-position'),third);
  await page.locator(`[data-position="${reserve}"]`).getByRole('link',{name:'Reserve füllen'}).click();
  await page.waitForLoadState('load');
  await page.waitForFunction(()=>document.querySelector('#library-search')?.dataset.enhanced==='ready');
  await page.getByLabel('Titel oder Alias',{exact:false}).fill('abba');
 await page.waitForFunction(()=>document.querySelector('#library-results').dataset.query==='abba');
 await page.getByRole('checkbox',{name:'Kontrollierten Austausch bestätigen; Zuordnungen erneut prüfen'}).check();
 await submit(page.getByRole('button',{name:'An dieser Position übernehmen'}));
 assert.match(await page.locator(`[data-position="${reserve}"]`).innerText(),/ABBA synthetic/);
 await page.getByRole('link',{name:'Stück aus Bibliothek hinzufügen'}).click();await submit(page.getByRole('button',{name:'Arrangement hinzufügen'}));
 assert.equal(await rows().count(),4);assert.deepEqual(external,[]);
 }finally{await browser.close();}
}
check(new URL(process.argv[2]).origin,...process.argv.slice(3)).catch(e=>{console.error(e);process.exitCode=1;});
