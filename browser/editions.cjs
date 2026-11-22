const assert = require('node:assert/strict');
const { chromium } = require('playwright-core');
async function check(origin, arrangement, part, first, second, file) {
    const browser = await chromium.launch({channel: process.env.BROWSER_CHANNEL || 'chrome'});
    try {
        const context = await browser.newContext({serviceWorkers: 'block'});
        const external = [], errors = [];
        await context.route('**/*', route => {
            if (new URL(route.request().url()).origin === origin) return route.continue();
            external.push(route.request().url()); return route.abort();
        });
        const page = await context.newPage();
        page.on('pageerror', e => errors.push(e.message));
        const url = `${origin}/archive/library/${arrangement}/parts/${part}/editions/`;
        await page.goto(url);
        await page.getByLabel('Benutzername').fill('editions-browser');
        await page.getByLabel('Passwort').fill('Synthetic-editions-135');
        await page.getByRole('button', {name: 'Anmelden'}).click();
        await page.waitForLoadState('load');
        assert.match(await page.locator('body').innerText(), /Mehrere passende Ausgaben/);
        async function prefer(id) {
            await page.locator(`form:has(input[name="assignment"][value="${id}"]) button`).click();
            await page.getByText('Archivweite Bevorzugung gespeichert.', {exact: false}).waitFor();
        }
        await prefer(first);
        await page.reload();
        assert.match(await page.locator('body').innerText(), /Archivweit bevorzugt/);
        const pinned = await context.newPage();
        await pinned.goto(url + `?selection=${first}`);
        await prefer(second);
        await pinned.reload();
        assert.match(await pinned.locator('body').innerText(), new RegExp(`Explizite Ausgabenwahl · ${file}`));
        await page.getByRole('button', {name:'Archiv-Bevorzugung zurücksetzen'}).click();
        await page.reload();
        assert.match(await page.locator('body').innerText(), /Mehrere passende Ausgaben/);
        assert.deepEqual(external, []); assert.deepEqual(errors, []);
    } finally { await browser.close(); }
}
check(new URL(process.argv[2]).origin, ...process.argv.slice(3)).catch(error => {console.error(error); process.exitCode=1;});
