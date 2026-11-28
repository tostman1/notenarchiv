const assert = require("node:assert/strict");
const { chromium } = require("playwright-core");
async function check(origin, arrangement, instrument, part, ids, mode) {
    const browser = await chromium.launch({ channel: process.env.BROWSER_CHANNEL || "chrome" });
    try {
        const context = await browser.newContext({ serviceWorkers: "block" });
        await context.route("**/*", route => new URL(route.request().url()).origin === origin ? route.continue() : route.abort());
        const page = await context.newPage();
        await page.goto(`${origin}/archive/review/`);
        await page.getByLabel("Benutzername").fill("batch-browser");
        await page.getByLabel("Passwort").fill("Synthetic-batch-135");
        await page.getByRole("button", { name: "Anmelden" }).click();
        assert.equal(await page.locator('input[name="versions"]').count(), 0);
        for (const [index, id] of ids.entries()) {
            await page.goto(`${origin}/archive/review/${id}/`);
            await page.locator('#pdf-preview[data-rendered="true"]').waitFor();
            if (!index) assert.equal(await page.getByRole("link", { name: "Nächste Version", exact: true }).count(), 1);
            else assert.equal(await page.getByRole("link", { name: "Vorherige Version", exact: true }).count(), 1);
            const correction = page.locator('form:has(input[name="action"][value="save"])');
            await correction.getByLabel("Arrangement / Ausgabe", { exact: false }).selectOption(arrangement);
            await page.getByLabel("Instrumentenvarianten", { exact: false }).selectOption(instrument);
            await page.getByLabel("Musikalische Stimmen", { exact: false }).selectOption(part);
            await page.getByRole("button", { name: "Zuordnung speichern" }).click();
            await page.locator('#pdf-preview[data-rendered="true"]').waitFor();
            await page.getByLabel("Ich habe alle Seiten", { exact: false }).check();
            await page.getByRole("button", { name: "Visuelle Prüfung speichern" }).click();
            await page.getByText("Von Ihnen für diese Version und Zuordnung visuell geprüft.", { exact: true }).waitFor();
        }
        await page.goto(`${origin}/archive/review/`);
        await page.reload();
        assert.equal(await page.locator('input[name="versions"]').count(), 2);
        if (mode === "approve") {
            for (const checkbox of await page.locator('input[name="versions"]').all()) await checkbox.check();
            await page.getByLabel("Ausgewählte einzeln geprüfte", { exact: false }).check();
            await page.getByRole("button", { name: "Stapel-Freigabe beauftragen" }).click();
            await page.getByText("Freigabeaufträge erstellt: 2.", { exact: false }).waitFor();
            assert.equal(await page.locator('input[name="versions"]').count(), 0);
        }
    } finally { await browser.close(); }
}
check(new URL(process.argv[2]).origin, process.argv[3], process.argv[4], process.argv[5], process.argv.slice(6, 8), process.argv[8])
    .catch(error => { console.error(error); process.exitCode = 1; });
