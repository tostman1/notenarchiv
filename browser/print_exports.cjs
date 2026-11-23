const assert=require('node:assert/strict');const {chromium}=require('playwright-core');
async function run(origin,id){
 const browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL||'chrome'});
 try{
  const context=await browser.newContext({serviceWorkers:'block',acceptDownloads:true}),errors=[];
  await context.route('**/*',route=>new URL(route.request().url()).origin===origin?route.continue():route.abort());
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  await page.goto(`${origin}/exports/runs/${id}/`);
  await page.getByLabel('Benutzername').fill('synthetic-editions');await page.getByLabel('Passwort').fill('Synthetic-print-135');
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Anmelden'}).click()]);
  await Promise.all([page.waitForNavigation({waitUntil:'load'}),page.getByRole('button',{name:'Separate Druck-PDF erstellen'}).click()]);
  const link=page.getByRole('link',{name:'Druck-PDF-Vorschau',exact:true});
  for(let i=0;i<100&&!(await link.count());i++){await page.reload({waitUntil:'load'});await page.waitForTimeout(250);}
  assert.equal(await link.count(),1);await link.click();
  await page.locator('#pdf-preview[data-rendered="true"]').waitFor();assert.equal(await page.locator('#pdf-count').innerText(),'4');
  const [file]=await Promise.all([page.waitForEvent('download'),page.getByRole('link',{name:'Druck-PDF herunterladen',exact:true}).click()]);
  assert.equal(await file.failure(),null);assert.equal(file.suggestedFilename(),'Druck-PDF.pdf');assert.deepEqual(errors,[]);
 }finally{await browser.close();}
}
run(new URL(process.argv[2]).origin,process.argv[3]).catch(e=>{console.error(e);process.exitCode=1;});
