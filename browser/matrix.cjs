const assert=require('node:assert/strict');const {chromium}=require('playwright-core');
async function check(origin,project,position,person,file,reserve){
 const browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL||'chrome'});
 try{
 const ctx=await browser.newContext({serviceWorkers:'block'}),external=[],errors=[];
 await ctx.route('**/*',route=>{if(new URL(route.request().url()).origin===origin)return route.continue();external.push(route.request().url());return route.abort();});
 const page=await ctx.newPage();page.on('pageerror',e=>errors.push(e.message));await page.goto(`${origin}/projects/${project}/matrix/`);
 await page.getByLabel('Benutzername').fill('synthetic-editions');await page.getByLabel('Passwort').fill('Synthetic-matrix-135');
 await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Anmelden'}).click()]);
 const cell=page.locator(`tr[data-position="${position}"] td[data-participant="${person}"]`);
 assert.equal(await cell.getAttribute('data-status'),'AVAILABLE');assert.match(await cell.innerText(),/Persönlicher Stück-Override/);assert.match(await cell.innerText(),new RegExp(file));
 assert.match(await page.locator('thead').innerText(),/Mathias/);assert.match(await page.locator('thead').innerText(),/Sebi/);assert.match(await page.locator('thead').innerText(),/Riccardo/);
 assert.equal(await page.locator(`tr[data-position="${reserve}"] :is(select,button,a,input)`).count(),0);
 assert.equal(await page.locator('#assignment-matrix tbody tr').count(),3);
 await page.reload();assert.equal(await cell.getAttribute('data-status'),'AVAILABLE');
 await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 assert.deepEqual(external,[]);assert.deepEqual(errors,[]);
 }finally{await browser.close();}
}
check(new URL(process.argv[2]).origin,...process.argv.slice(3)).catch(e=>{console.error(e);process.exitCode=1;});
