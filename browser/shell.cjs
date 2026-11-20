const assert = require("node:assert/strict");
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
        assert.deepEqual(await nav.getByRole("link").allTextContents(), ["Übersicht"]);
        assert.deepEqual(await nav.locator('[aria-disabled="true"]').allTextContents(), [
            "Notenbibliothek", "Indizierung", "Prüfwarteschlange", "Projekte", "Scanaufbereitung",
            "Mitglieder", "Instrumente und Stimmen", "Aufträge", "Einstellungen",
        ]);
        assert.equal(await nav.locator("li :is(a, button, [tabindex])").count(), 0);
        assert.equal(await nav.getByText("Debug / Logs").count(), 0);
        assert.equal(await page.locator(".dashboard").evaluate(el => getComputedStyle(el).display), "grid");
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
