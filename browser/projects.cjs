const assert=require('node:assert/strict');
const {chromium}=require('playwright-core');
async function check(origin){
 const browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL||'chrome'});
 try{
  const ctx=await browser.newContext({serviceWorkers:'block'}),external=[];
  await ctx.route('**/*',route=>{if(new URL(route.request().url()).origin===origin)return route.continue();external.push(route.request().url());return route.abort();});
   const page=await ctx.newPage();await page.goto(origin+'/projects/');
   async function submit(target,button,status=200){
    const [response]=await Promise.all([target.waitForNavigation({waitUntil:'load'}),button.click()]);
    assert.equal(response.status(),status);
   }
   await page.getByLabel('Benutzername').fill('projects-browser');await page.getByLabel('Passwort').fill('Synthetic-projects-135');await submit(page,page.getByRole('button',{name:'Anmelden'}));
  await page.getByRole('link',{name:'Neues Projekt'}).click();
   await page.getByLabel('Projektname').fill('Synthetic project');await submit(page,page.getByRole('button',{name:'Projekt speichern'}));
  await page.getByRole('heading',{name:'Synthetic project',exact:true}).waitFor();
  const source=page.url();const stale=await ctx.newPage();await stale.goto(source+'edit/');
   await page.getByRole('link',{name:'Projekt bearbeiten'}).click();await page.getByLabel('Projektname').fill('Synthetic changed');await submit(page,page.getByRole('button',{name:'Projekt speichern'}));
   await stale.getByLabel('Projektname').fill('Lost update');await submit(stale,stale.getByRole('button',{name:'Projekt speichern'}),409);await stale.getByText('Das Projekt wurde inzwischen geändert.',{exact:false}).waitFor();
   await page.getByLabel('Name der Kopie').fill('Synthetic changed');await submit(page,page.getByRole('button',{name:'Projekt duplizieren'}));
   assert.notEqual(page.url(),source);await page.reload();await submit(page,page.getByRole('button',{name:'Projekt archivieren'}));await page.getByRole('button',{name:'Projekt reaktivieren'}).waitFor();
  await page.goto(source);await page.getByRole('heading',{name:'Synthetic changed',exact:true}).waitFor();
  assert.deepEqual(external,[]);
 }finally{await browser.close();}
}
check(new URL(process.argv[2]).origin).catch(e=>{console.error(e);process.exitCode=1;});
