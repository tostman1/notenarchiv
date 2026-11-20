const assert = require("node:assert/strict");
const fs = require("node:fs");
const { chromium } = require("playwright-core");

async function smoke(origin, logFile) {
    const browser = await chromium.launch({ channel: process.env.BROWSER_CHANNEL || "chrome" });
    try {
        const context = await browser.newContext({ serviceWorkers: "block" });
        const external = [];
        await context.route("**/*", route => {
            if (new URL(route.request().url()).origin === origin) return route.continue();
            external.push(route.request().url());
            return route.abort();
        });
        const page = await context.newPage();
        await page.goto(`${origin}/diagnostics/`);
        assert.equal(new URL(page.url()).pathname, "/login/");
        await page.getByLabel("Benutzername").fill("synthetic-debug");
        await page.getByLabel("Passwort").fill("Synthetic-browser-135");
        await page.getByRole("button", { name: "Anmelden" }).click();
        await page.getByRole("heading", { name: "Debug / Logs" }).waitFor();
        assert.equal(await page.locator(".mode-badge").innerText(), "Diagnosemodus");
        assert.equal(await page.locator('#log-records tr').count(), 1);
        assert.equal(await page.getByRole("navigation").locator('[aria-current="page"]').innerText(), "Debug / Logs");
        assert.ok(!(await page.content()).includes("synthetic secret"));
        await page.getByLabel("Dienst").selectOption("worker");
        await page.getByRole("button", { name: "Filtern", exact: true }).click();
        await page.getByText("Keine passenden Meldungen in diesem Ausschnitt.").waitFor();
        await page.getByLabel("Dienst").selectOption("web");
        await page.getByLabel("Stufe").selectOption("INFO");
        await page.getByRole("button", { name: "Filtern", exact: true }).click();
        await page.locator('#log-records tr').waitFor();
        await page.getByRole("button", { name: "Live-Aktualisierung starten" }).click();
        fs.appendFileSync(logFile, JSON.stringify({
            timestamp: "2026-11-20T12:01:00+00:00", level: "INFO", component: "jobs",
            service: "web", event: "job_started", message: "synthetic secret",
        }) + "\n");
        await page.locator("#log-records").getByText("job_started").waitFor();
        await page.getByRole("button", { name: "Live-Aktualisierung stoppen" }).click();
        const downloadPromise = page.waitForEvent("download");
        await page.getByRole("link", { name: /Bereinigten Ausschnitt herunterladen/ }).click();
        const download = await downloadPromise;
        assert.equal(download.suggestedFilename(), "diagnostics-web.jsonl");
        let text = "";
        for await (const chunk of await download.createReadStream()) text += chunk.toString("utf8");
        assert.equal(text.trim().split("\n").length, 2);
        assert.ok(!text.includes("synthetic secret"));
        assert.ok(!text.includes("<script>"));
        await page.getByRole("button", { name: "Abmelden" }).click();
        await page.goto(`${origin}/diagnostics/records/`);
        assert.equal(new URL(page.url()).pathname, "/login/");
        assert.deepEqual(external, []);
    } finally {
        await browser.close();
    }
}

smoke(new URL(process.argv[2]).origin, process.argv[3]).catch(error => {
    console.error(error);
    process.exitCode = 1;
});
