const assert = require("node:assert/strict");
const { chromium } = require("playwright-core");

async function check(origin, mode, folder) {
    const browser = await chromium.launch({ channel: process.env.BROWSER_CHANNEL || "chrome" });
    try {
        const context = await browser.newContext({ serviceWorkers: "block" });
        const external = [], errors = [];
        await context.route("**/*", route => {
            if (new URL(route.request().url()).origin === origin) return route.continue();
            external.push(route.request().url()); return route.abort();
        });
        const page = await context.newPage();
        page.on("pageerror", error => errors.push(error.message));
        await page.goto(`${origin}/archive/index/`);
        assert.equal(new URL(page.url()).pathname, "/login/");
        await page.getByLabel("Benutzername").fill("index-browser");
        await page.getByLabel("Passwort").fill("Synthetic-index-135");
        await page.getByRole("button", { name: "Anmelden" }).click();
        if (mode === "queue") {
            await page.getByLabel("Auswahl indizieren", { exact: false }).check();
            await page.getByRole("button", { name: "Indizieren", exact: true }).click();
            await page.getByText("Wartend", { exact: true }).waitFor();
            await page.getByRole("button", { name: "Abbrechen", exact: true }).click();
            await page.getByText("Abgebrochen", { exact: true }).waitFor();
            await page.goto(`${origin}/archive/index/`);
            await page.getByLabel("RAW-Unterordner", { exact: false }).fill("Synthetic selected");
            await page.getByLabel("Auswahl indizieren", { exact: false }).check();
            await page.getByRole("button", { name: "Indizieren", exact: true }).click();
            await page.getByText("Wartend", { exact: true }).waitFor();
        } else {
            await page.goto(`${origin}/archive/index/folders/${folder}/`);
            await page.getByText("STATUS-JSON veröffentlicht und geprüft.", { exact: true }).waitFor();
            assert.match(await page.locator("body").innerText(), /Textmarker allein beweist weder/);
            await page.getByRole("link", { name: /Versionen visuell prüfen/ }).click();
            await page.getByText("Synthetic selected/unknown.pdf", { exact: false }).waitFor();
            assert.equal(await page.getByRole("link", { name: "PDF-Vorschau", exact: true }).count(), 1);
            await page.reload();
        }
        assert.deepEqual(external, []); assert.deepEqual(errors, []);
    } finally { await browser.close(); }
}
check(new URL(process.argv[2]).origin, process.argv[3], process.argv[4]).catch(error => {
    console.error(error); process.exitCode = 1;
});
