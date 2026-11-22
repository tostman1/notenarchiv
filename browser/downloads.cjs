const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const {chromium} = require('playwright-core');
async function bytes(download) {
    const stream = await download.createReadStream(), chunks=[];
    for await (const chunk of stream) chunks.push(chunk);
    return Buffer.concat(chunks);
}
async function check(origin, arrangement, first, second, hash1, hash2) {
    const browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL||'chrome'});
    try {
        const context=await browser.newContext({serviceWorkers:'block',acceptDownloads:true});
        const external=[];
        await context.route('**/*', route=>{
            if(new URL(route.request().url()).origin===origin) return route.continue();
            external.push(route.request().url()); return route.abort();
        });
        const page=await context.newPage();
        const url=`${origin}/archive/library/${arrangement}/`;
        await page.goto(url);
        await page.getByLabel('Benutzername').fill('downloads-browser');
        await page.getByLabel('Passwort').fill('Synthetic-downloads-135');
        await page.getByRole('button',{name:'Anmelden'}).click();
        await page.waitForLoadState('load');
        const direct=page.waitForEvent('download');
        await page.locator(`a[href="/archive/notes/${first}/download/"]`).click();
        const pdf=await bytes(await direct);
        assert.equal(crypto.createHash('sha256').update(pdf).digest('hex'),hash1);
        for(const id of [first,second]) await page.locator(`input[name="file"][value="${id}"]`).check();
        await page.getByRole('button',{name:'Gewählte Archivnoten herunterladen'}).click();
        assert.match(await page.locator('body').innerText(),/2 PDFs/);
        assert.match(await page.locator('body').innerText(),/eine Kopie/);
        const zipPromise=page.waitForEvent('download');
        await page.getByRole('button',{name:'ZIP herunterladen'}).click();
        const zip=await bytes(await zipPromise);
        assert.equal(zip.readUInt32LE(0),0x04034b50);
        let offset=0, hashes=[];
        while(zip.readUInt32LE(offset)===0x04034b50){
            assert.equal(zip.readUInt16LE(offset+8),0);
            const size=zip.readUInt32LE(offset+18), name=zip.readUInt16LE(offset+26), extra=zip.readUInt16LE(offset+28);
            const start=offset+30+name+extra;
            hashes.push(crypto.createHash('sha256').update(zip.subarray(start,start+size)).digest('hex'));
            offset=start+size;
        }
        assert.deepEqual(hashes.sort(),[hash1,hash2].sort());
        assert.deepEqual(external,[]);
    } finally {await browser.close();}
}
check(new URL(process.argv[2]).origin,...process.argv.slice(3)).catch(e=>{console.error(e);process.exitCode=1;});
