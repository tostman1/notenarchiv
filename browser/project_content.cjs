const assert=require('node:assert/strict');const {chromium}=require('playwright-core');
async function run(origin,project,person,position,edition){
 const browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL||'chrome'});
 try{
  const context=await browser.newContext({serviceWorkers:'block'}),errors=[];
  await context.route('**/*',route=>new URL(route.request().url()).origin===origin?route.continue():route.abort());
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  await page.goto(`${origin}/projects/${project}/matrix/`);
  await page.getByLabel('Benutzername').fill('synthetic-editions');
  await page.getByLabel('Passwort').fill('Synthetic-project-content-135');
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Anmelden'}).click()]);
  assert.match(await page.locator('body').innerText(),new RegExp(edition));
  const url=`${origin}/projects/${project}/excerpts/`;await page.goto(url);
  for(const input of await page.locator('input[name="participants"]').all())await input.setChecked(await input.getAttribute('value')===person);
  for(const input of await page.locator('input[name="positions"]').all())await input.setChecked(await input.getAttribute('value')===position);
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Auswahl prüfen'}).click()]);
  assert.equal(await page.getByRole('link',{name:/Originalkontext/}).count(),1);
  const payload=await page.locator('input[name="token"]').evaluate(node=>Array.from(new FormData(node.form).entries()));
  const submit=async tamper=>page.evaluate(async({url,payload,tamper})=>{
   const body=new URLSearchParams(payload);body.set('action','authorize');if(tamper)body.set('token','invalid');
   const response=await fetch(url,{method:'POST',body});return{status:response.status,text:await response.text()};
  },{url,payload,tamper});
  assert.equal((await submit(true)).status,409);
  const result=await submit(false);assert.equal(result.status,200);
  assert.match(result.text,/Unveränderliche Generierungseingaben gespeichert/);
  assert.equal((await submit(false)).status,200);assert.deepEqual(errors,[]);
 }finally{await browser.close();}
}
run(new URL(process.argv[2]).origin,...process.argv.slice(3)).catch(e=>{console.error(e);process.exitCode=1;});
