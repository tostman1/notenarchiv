const assert = require("node:assert/strict");
const { chromium } = require("playwright-core");

async function test(origin, ids) {
    const browser = await chromium.launch({ channel: process.env.BROWSER_CHANNEL || "chrome" });
    try {
        const context = await browser.newContext({ serviceWorkers: "block" });
        const external = [], errors = [], failed = [], workers = [];
        await context.route("**/*", route => {
            if (new URL(route.request().url()).origin === origin) return route.continue();
            external.push(route.request().url());
            return route.abort();
        });
        const page = await context.newPage();
        page.on("pageerror", error => errors.push(error.message));
        page.on("response", response => { if (response.status() >= 400) failed.push(response.url()); });
        page.on("worker", worker => workers.push(worker.url()));
        await page.goto(`${origin}/archive/preview/${ids[0]}/`);
        assert.equal(new URL(page.url()).pathname, "/login/");
        await page.getByLabel("Benutzername").fill("preview-browser");
        await page.getByLabel("Passwort").fill("Synthetic-preview-135");
        await page.getByRole("button", { name: "Anmelden" }).click();
        for (const [index, id] of ids.entries()) {
            await page.goto(`${origin}/archive/preview/${id}/`);
            await page.locator('#pdf-preview[data-rendered="true"][data-page="1"]').waitFor();
            assert.equal(await page.locator("#pdf-count").innerText(), "2");
            await page.getByText(index ? "Bestätigte Version" : "Ungeprüfte Version", { exact: false }).waitFor();
            const canvas = page.locator("#pdf-canvas");
            const width = await canvas.evaluate(el => el.width);
            assert.ok(await canvas.evaluate(el => {
                const data = el.getContext("2d").getImageData(0, 0, el.width, el.height).data;
                for (let i = 0; i < data.length; i += 4) if (data[i] < 100 && data[i+3] > 0) return true;
                return false;
            }));
            await page.getByLabel("Zoom", { exact: true }).selectOption("1.5");
            await page.locator('#pdf-preview[data-rendered="true"][data-zoom="1.5"]').waitFor();
            assert.ok(await canvas.evaluate(el => el.width) > width);
            await page.getByRole("button", { name: "Nächste Seite" }).click();
            await page.locator('#pdf-preview[data-rendered="true"][data-page="2"]').waitFor();
            assert.equal(await page.getByRole("button", { name: "Nächste Seite" }).isDisabled(), true);
            await page.getByLabel("Seite", { exact: true }).fill("1");
            await page.getByLabel("Seite", { exact: true }).press("Tab");
            await page.locator('#pdf-preview[data-rendered="true"][data-page="1"]').waitFor();
            await page.getByRole("button", { name: "Nächste Seite" }).click();
            await page.locator('#pdf-preview[data-rendered="true"][data-page="2"]').waitFor();
            await page.getByRole("button", { name: "Vorherige Seite" }).click();
            await page.locator('#pdf-preview[data-rendered="true"][data-page="1"]').waitFor();
            assert.equal(await page.locator('#pdf-preview :is(a, iframe, object, embed)').count(), 0);
            const thumbnail = await page.request.get(`${origin}/archive/preview/${id}/thumbnail/1/`);
            assert.equal(thumbnail.status(), 200);
            assert.equal(thumbnail.headers()["content-type"], "image/png");
            await page.reload();
            await page.locator('#pdf-preview[data-rendered="true"]').waitFor();
        }
        assert.ok(workers.some(url => url.endsWith("/pdf.worker.mjs")));
        assert.deepEqual(errors, []);
        assert.deepEqual(failed, []);
        assert.deepEqual(external, []);
        await page.getByRole("button", { name: "Abmelden" }).click();
        for (const endpoint of ["", "document/", "thumbnail/1/"]) {
            const response = await page.request.get(`${origin}/archive/preview/${ids[0]}/${endpoint}`, { maxRedirects: 0 });
            assert.equal(response.status(), 302);
        }
    } finally { await browser.close(); }
}
test(new URL(process.argv[2]).origin, process.argv.slice(3)).catch(error => {
    console.error(error);
    process.exitCode = 1;
});
