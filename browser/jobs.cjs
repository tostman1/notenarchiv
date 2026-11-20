const assert = require("node:assert/strict");
const { chromium } = require("playwright-core");

async function check(origin, active, completed, failed) {
    const browser = await chromium.launch({ channel: process.env.BROWSER_CHANNEL || "chrome" });
    try {
        const context = await browser.newContext({ serviceWorkers: "block" });
        await context.route("**/*", route => new URL(route.request().url()).origin === origin
            ? route.continue() : route.abort());
        const page = await context.newPage();
        await page.goto(`${origin}/jobs/`);
        assert.equal(new URL(page.url()).pathname, "/login/");
        await page.getByLabel("Benutzername").fill("synthetic-jobs");
        await page.getByLabel("Passwort").fill("Synthetic-browser-135");
        await page.getByRole("button", { name: "Anmelden" }).click();
        await page.getByRole("heading", { name: "Aufträge", exact: true }).waitFor();
        for (const state of ["Wartend", "Läuft", "Abgeschlossen", "Fehlgeschlagen"]) {
            await page.getByRole("cell", { name: state, exact: true }).waitFor();
        }
        assert.match(await page.locator('[role="status"]').innerText(), /Hintergrunddienst verfügbar/);
        await page.goto(`${origin}/jobs/${failed}/`);
        assert.match(await page.getByRole("alert").innerText(), /Verarbeitung ist fehlgeschlagen/);
        assert.ok(!(await page.locator("body").innerText()).includes("synthetic-private"));
        await page.goto(`${origin}/jobs/${completed}/`);
        assert.equal(await page.locator("progress").getAttribute("value"), "100");
        await page.goto(`${origin}/jobs/${active}/`);
        assert.equal(await page.locator("progress").getAttribute("value"), "40");
        await page.setViewportSize({ width: 390, height: 844 });
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        await page.getByRole("button", { name: "Abbrechen", exact: true }).click();
        const deadline = Date.now() + 10000;
        while ((await page.locator("#job-status").innerText()) !== "Abgebrochen" && Date.now() < deadline) {
            await page.getByRole("link", { name: "Aktualisieren", exact: true }).click();
            await page.waitForTimeout(100);
        }
        assert.equal(await page.locator("#job-status").innerText(), "Abgebrochen");
        assert.equal(await page.getByRole("button", { name: "Abbrechen", exact: true }).count(), 0);
    } finally {
        await browser.close();
    }
}
check(new URL(process.argv[2]).origin, ...process.argv.slice(3)).catch(error => {
    console.error(error);
    process.exitCode = 1;
});
