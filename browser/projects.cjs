const assert=require('node:assert/strict');
const {chromium}=require('playwright-core');
async function check(origin){
 const browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL||'chrome'});
 try{
  const ctx=await browser.newContext({serviceWorkers:'block'}),external=[];
  await ctx.route('**/*',route=>{if(new URL(route.request().url()).origin===origin)return route.continue();external.push(route.request().url());return route.abort();});
  const page=await ctx.newPage();await page.goto(origin+'/projects/');
  await page.getByLabel('Benutzername').fill('projects-browser');await page.getByLabel('Passwort').fill('Synthetic-projects-135');await page.getByRole('button',{name:'Anmelden'}).click();
  await page.getByRole('link',{name:'Neues Projekt'}).click();
  await page.getByLabel('Projektname').fill('Synthetic project');await page.getByRole('button',{name:'Projekt speichern'}).click();
  await page.getByRole('heading',{name:'Synthetic project',exact:true}).waitFor();
  const source=page.url();const stale=await ctx.newPage();await stale.goto(source+'edit/');
  await page.getByRole('link',{name:'Projekt bearbeiten'}).click();await page.getByLabel('Projektname').fill('Synthetic changed');await page.getByRole('button',{name:'Projekt speichern'}).click();
  await stale.getByLabel('Projektname').fill('Lost update');await stale.getByRole('button',{name:'Projekt speichern'}).click();await stale.getByText('Das Projekt wurde inzwischen geändert.',{exact:false}).waitFor();
  await page.getByLabel('Name der Kopie').fill('Synthetic changed');await page.getByRole('button',{name:'Projekt duplizieren'}).click();
  assert.notEqual(page.url(),source);await page.reload();await page.getByRole('button',{name:'Projekt archivieren'}).click();await page.getByRole('button',{name:'Projekt reaktivieren'}).waitFor();
  await page.goto(source);await page.getByRole('heading',{name:'Synthetic changed',exact:true}).waitFor();
  assert.deepEqual(external,[]);
 }finally{await browser.close();}
}
check(new URL(process.argv[2]).origin).catch(e=>{console.error(e);process.exitCode=1;});
