const assert=require('node:assert/strict');const {chromium}=require('playwright-core');
async function run(origin,project,person){
 const browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL||'chrome'});
 try{
  const context=await browser.newContext({serviceWorkers:'block'}),errors=[];
  await context.route('**/*',route=>new URL(route.request().url()).origin===origin?route.continue():route.abort());
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  const url=`${origin}/projects/${project}/preflight/`;
  await page.goto(url);await page.getByLabel('Benutzername').fill('synthetic-editions');
  await page.getByLabel('Passwort').fill('Synthetic-snapshot-135');
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Anmelden'}).click()]);
  for(const input of await page.locator('input[name="participants"]').all())await input.setChecked(await input.getAttribute('value')===person);
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Auswahl prüfen'}).click()]);
  const payload=await page.locator('input[name="token"]').evaluate(node=>{
   const form=node.form;return Object.fromEntries(new FormData(form));
  });
  const positions=await page.locator('input[type="hidden"][name="positions"]').evaluateAll(nodes=>nodes.map(n=>n.value));
  const keys=await page.locator('input[name="acknowledgements"]').evaluateAll(nodes=>nodes.map(n=>n.value));
  const submit=async acknowledgements=>page.evaluate(async ({url,payload,positions,acknowledgements})=>{
   const body=new URLSearchParams();for(const [key,value]of Object.entries(payload))if(!['positions','participants','acknowledgements'].includes(key))body.append(key,value);
   body.set('action','authorize');body.append('participants',document.querySelector('input[type="hidden"][name="participants"]').value);
   for(const value of positions)body.append('positions',value);for(const value of acknowledgements)body.append('acknowledgements',value);
   const response=await fetch(url,{method:'POST',body});return {status:response.status,text:await response.text()};
  },{url,payload,positions,acknowledgements});
  assert.equal((await submit([])).status,409);
  const first=await submit(keys);assert.equal(first.status,200);assert.match(first.text,/Unveränderliche Generierungseingaben gespeichert/);
  assert.equal((await submit(keys)).status,200);
   assert.match(first.text,/Ergebnis und Auftrag öffnen/);assert.deepEqual(errors,[]);
 }finally{await browser.close();}
}
run(new URL(process.argv[2]).origin,...process.argv.slice(3)).catch(e=>{console.error(e);process.exitCode=1;});
