const assert=require('node:assert/strict');const {chromium}=require('playwright-core');
async function check(mode,origin,project,member,first,second){
 const browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL||'chrome'});
 try{
 const ctx=await browser.newContext({serviceWorkers:'block'}),external=[];
 await ctx.route('**/*',route=>{if(new URL(route.request().url()).origin===origin)return route.continue();external.push(route.request().url());return route.abort();});
 const page=await ctx.newPage(),url=`${origin}/projects/${project}/participants/`;
 async function submit(button){
  const [response]=await Promise.all([page.waitForNavigation({waitUntil:'load'}),button.click()]);
  assert.equal(response.status(),200);
 }
 await page.goto(url);await page.getByLabel('Benutzername').fill('participants-browser');await page.getByLabel('Passwort').fill('Synthetic-participants-135');await page.getByRole('button',{name:'Anmelden'}).click();await page.waitForLoadState('load');
 if(mode==='select'){
  await page.locator(`input[name="member"][value="${member}"]`).check();await submit(page.getByRole('button',{name:'Auswahl dieser Seite speichern'}));
  await page.getByLabel('Name des Gasts').fill('Synthetic project guest');await page.getByLabel('Spielbare Gaststimme').selectOption(first);await submit(page.getByRole('button',{name:'Gast hinzufügen'}));
 await page.reload();assert.match(await page.locator('body').innerText(),/Synthetic project guest/);
 }else{
 const row=page.locator('li').filter({has:page.locator('p').filter({hasText:'Aktuelle Mitgliedsstimme'})}).filter({hasText:'Synthetic member 1'});
 const defaultLink=row.getByRole('link',{name:'Projektstimme ändern'});await defaultLink.click();
 assert.equal(await page.getByLabel('Gespeicherte Projektstimme').inputValue(),first);
 await page.goto(url);
  await submit(page.getByRole('button',{name:'Aktuelle Mitgliedsstimme ausdrücklich übernehmen'}));
 await page.getByRole('link',{name:'Projektstimme ändern'}).first().click();
 assert.equal(await page.getByLabel('Gespeicherte Projektstimme').inputValue(),second);
 await page.goto(url);assert.match(await page.locator('body').innerText(),/Persönliche Overrides bleiben/);
 }
 assert.deepEqual(external,[]);
 }finally{await browser.close();}
}
check(process.argv[2],new URL(process.argv[3]).origin,...process.argv.slice(4)).catch(e=>{console.error(e);process.exitCode=1;});
