const assert = require("node:assert/strict");
const { chromium } = require("playwright-core");
async function check(origin, id, template) {
    const browser = await chromium.launch({ channel: process.env.BROWSER_CHANNEL || "chrome" });
    try {
        const context = await browser.newContext({ serviceWorkers: "block" });
        const external = [], errors = [];
        await context.route("**/*", route => {
            if (new URL(route.request().url()).origin === origin) return route.continue();
            external.push(route.request().url()); return route.abort();
        });
        const page = await context.newPage(); page.on('pageerror', error => errors.push(error.message));
        await page.goto(`${origin}/archive/library/`);
        assert.equal(new URL(page.url()).pathname, '/login/');
        await page.getByLabel('Benutzername').fill('library-browser');
        await page.getByLabel('Passwort').fill('Synthetic-library-135');
        await page.getByRole('button', { name: 'Anmelden' }).click();
        await page.waitForLoadState('load');
        const search = page.getByLabel('Titel oder Alias', { exact: false });
        await search.fill('ａｂ');
        await page.waitForFunction(() => document.querySelector('#library-results').dataset.query === 'ａｂ'
            && document.querySelectorAll('#library-results tbody tr').length === 4);
        assert.match(await page.locator('#library-results').innerText(), /Fuchsgraben Polka/);
        await search.fill('graben');
        await page.waitForFunction(() => document.querySelector('#library-results').dataset.query === 'graben'
            && document.querySelectorAll('#library-results tbody tr').length === 1);
        assert.match(await page.locator('#library-results').innerText(), /Fuchsgraben Polka/);
        await page.goto(`${origin}/archive/library/${id}/`);
        assert.match(await page.locator('body').innerText(), /Erwartung unbekannt/);
        assert.match(await page.locator('body').innerText(), /Bestätigt und hash-geprüft/);
        await page.getByLabel('Besetzungsvorlage', { exact: false }).selectOption(template);
        await page.getByRole('button', { name: 'Vorlage übernehmen', exact: true }).click();
        await page.getByText('Die Besetzung wurde als unabhängige Erwartungsliste übernommen.').waitFor();
        await page.goto(`${origin}/archive/library/${id}/`);
        assert.match(await page.locator('body').innerText(), /Erforderliche Stimmen fehlen oder sind ungeprüft/);
        assert.match(await page.locator('tbody').innerText(), /Fehlend/);
        await page.reload();
        assert.equal(await page.locator('tbody tr').count(), 2);
        assert.deepEqual(external, []); assert.deepEqual(errors, []);
    } finally { await browser.close(); }
}
check(new URL(process.argv[2]).origin, process.argv[3], process.argv[4]).catch(error => {
    console.error(error); process.exitCode = 1;
});
