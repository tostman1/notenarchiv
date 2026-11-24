const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright-core");

async function smoke(origin) {
    const browser = await chromium.launch({ channel: process.env.BROWSER_CHANNEL || "chrome" });
    try {
        const context = await browser.newContext({ serviceWorkers: "block" });
        const external = [];
        const styles = [];
        await context.route("**/*", route => {
            if (new URL(route.request().url()).origin === origin) return route.continue();
            external.push(route.request().url());
            return route.abort();
        });
        const page = await context.newPage();
        page.on("response", response => {
            if (response.request().resourceType() === "stylesheet") styles.push(response.status());
        });
        await page.goto(origin);
        assert.equal(new URL(page.url()).pathname, "/login/");
        assert.equal(await page.getByRole("navigation").count(), 0);
        await page.keyboard.press("Tab");
        assert.equal(await page.locator(":focus").innerText(), "Zum Inhalt");
        await page.keyboard.press("Enter");
        assert.equal(await page.locator(":focus").getAttribute("id"), "inhalt");

        await page.getByLabel("Benutzername").fill("smoke-archivist");
        await page.getByLabel("Passwort").fill("invalid");
        await page.getByRole("button", { name: "Anmelden" }).click();
        await page.getByRole("alert").getByText("Benutzername oder Passwort ist falsch.").waitFor();
        await page.getByLabel("Passwort").fill("Synthetic-smoke-135");
        await page.getByRole("button", { name: "Anmelden" }).click();
        await page.getByRole("heading", { name: "Übersicht" }).waitFor();
        await page.reload();
        const nav = page.getByRole("navigation", { name: "Hauptnavigation" });
        assert.deepEqual(await nav.getByRole("link").allTextContents(), [
            "Übersicht", "Notenbibliothek", "Werke und Arrangements", "Instrumente und Stimmen", "Mitglieder",
            "Projekte", "Notenausgaben", "Indizierung", "Prüfwarteschlange", "Aufträge",
        ]);
        assert.deepEqual(await nav.locator('[aria-disabled="true"]').allTextContents(), [
            "Scanaufbereitung – Noch nicht verfügbar",
            "Einstellungen – Noch nicht verfügbar",
        ]);
        assert.equal(await nav.locator("li :is(a, button:not(:disabled), [tabindex])").count(), 0);
        assert.equal(await nav.getByText("Debug / Logs").count(), 0);
        assert.equal((await page.request.get(`${origin}/diagnostics/`)).status(), 404);
        assert.equal(await page.locator(".dashboard").evaluate(el => getComputedStyle(el).display), "grid");
        if (process.env.SCREENSHOT_DIR) {
            fs.mkdirSync(process.env.SCREENSHOT_DIR, { recursive: true });
            await page.screenshot({ path: path.join(process.env.SCREENSHOT_DIR, "preview-desktop.png"), fullPage: true });
        }
        await page.setViewportSize({ width: 390, height: 844 });
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        if (process.env.SCREENSHOT_DIR) {
            await page.screenshot({ path: path.join(process.env.SCREENSHOT_DIR, "preview-mobile.png"), fullPage: true });
        }
        await page.getByRole("button", { name: "Abmelden" }).click();
        await page.getByText("Sie wurden abgemeldet.").waitFor();
        await page.goto(origin);
        assert.equal(new URL(page.url()).pathname, "/login/");
        assert.ok(styles.length > 0 && styles.every(status => status === 200));
        assert.deepEqual(external, []);
    } finally {
        await browser.close();
    }
}

smoke(new URL(process.argv[2]).origin).catch(error => {
    console.error(error);
    process.exitCode = 1;
});
