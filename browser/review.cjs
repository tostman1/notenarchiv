const assert = require("node:assert/strict");
const { chromium } = require("playwright-core");

async function check(mode, origin, id, arrangement, instrument, parts) {
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
        await page.goto(`${origin}/archive/review/${id}/`);
        assert.equal(new URL(page.url()).pathname, "/login/");
        await page.getByLabel("Benutzername").fill("review-browser");
        await page.getByLabel("Passwort").fill("Synthetic-review-135");
        await page.getByRole("button", { name: "Anmelden" }).click();
        await page.locator('#pdf-preview[data-rendered="true"]').waitFor();
        if (mode === "selection") {
            const selection = page.locator("#ocr-selection");
            const image = page.locator(".ocr-evidence-image");
            await image.scrollIntoViewIfNeeded();
            await image.evaluate(element => element.decode());
            assert.ok(await image.evaluate(element => element.naturalWidth > 0));
            await page.getByRole("button", { name: "Quellseite anzeigen 2", exact: true }).click();
            await page.locator('#pdf-preview[data-rendered="true"][data-page="2"]').waitFor();
            assert.equal(await selection.locator('[name="page"]').inputValue(), "2");
            for (const [name, value] of Object.entries({ left: "10", top: "20", right: "80", bottom: "90" })) {
                await selection.locator(`[name="${name}"]`).fill(value);
            }
            await page.getByRole("button", { name: "Ausgewählten Bereich lokal analysieren", exact: true }).click();
            await page.getByText("Wartend", { exact: true }).waitFor();
        } else if (mode === "region") {
            const selection = page.locator("#ocr-selection");
            for (const [name, value] of Object.entries({ page: "2", left: "10", top: "20", right: "80", bottom: "90" })) {
                await selection.locator(`[name="${name}"]`).fill(value);
            }
            await page.getByRole("button", { name: "Bereich als neue unbestätigte Region speichern", exact: true }).click();
            const saved = page.locator("[data-region-id]");
            await saved.waitFor();
            assert.equal(await saved.getAttribute("data-region-number"), "1");
            await saved.click();
            await page.locator('#pdf-preview[data-rendered="true"][data-page="2"]').waitFor();
            assert.equal(await selection.locator('[name="expected_region_number"]').inputValue(), "1");
            assert.ok(Math.abs(Number(await selection.locator('[name="right"]').inputValue()) - 80) < 0.01);
            await selection.locator('[name="right"]').fill("70");
            await page.getByRole("button", { name: "Bereich als neue unbestätigte Region speichern", exact: true }).click();
            await page.locator('[data-region-number="2"]').waitFor();
            assert.equal(await page.locator('[data-region-number="1"]').count(), 0);
            await page.getByText("Unbestätigten Regionsauszug ansehen", { exact: false }).click();
            const regionImage = page.locator('img[src*="/region/"]');
            await regionImage.scrollIntoViewIfNeeded();
            await regionImage.evaluate(element => element.decode());
            assert.ok(await regionImage.evaluate(element => element.naturalWidth > 0));
            await page.locator('[data-region-number="2"]').click();
            await page.locator('#pdf-preview[data-rendered="true"][data-page="2"]').waitFor();
            await page.getByRole("button", { name: "Neue Region statt ausgewählter Region", exact: true }).click();
            assert.equal(await selection.locator('[name="region_id"]').inputValue(), "");
            assert.equal(await selection.locator('[name="expected_region_number"]').inputValue(), "0");
            let releaseDocument;
            const heldDocument = new Promise(resolve => { releaseDocument = resolve; });
            await page.route("**/archive/preview/**/document/", async route => {
                await heldDocument;
                await route.continue();
            });
            await page.reload({ waitUntil: "domcontentloaded" });
            const pendingRegion = page.locator('[data-region-number="2"]');
            assert.equal(await pendingRegion.isDisabled(), true);
            assert.equal(await page.locator('#ocr-selection [name="region_id"]').inputValue(), "");
            releaseDocument();
            await page.locator('#pdf-preview[data-rendered="true"]').waitFor();
            await pendingRegion.click();
            await page.locator('#pdf-preview[data-rendered="true"][data-page="2"]').waitFor();
            assert.equal(await page.locator('#ocr-selection [name="page"]').inputValue(), "2");
        } else if (mode === "inspect") {
            const selection = page.locator("#ocr-selection");
            await selection.locator('[name="left"]').fill("10");
            await selection.locator('[name="right"]').fill("70");
            await page.getByRole("button", { name: "Bereich aufziehen", exact: true }).click();
            const overlay = page.locator(".ocr-selection-overlay");
            assert.equal(await overlay.evaluate(element => getComputedStyle(element).pointerEvents), "auto");
            await overlay.scrollIntoViewIfNeeded();
            const box = await overlay.boundingBox();
            await page.mouse.move(box.x + box.width * 0.1, box.y + box.height * 0.1);
            await page.mouse.down();
            await page.mouse.move(box.x + box.width * 0.6, box.y + box.height * 0.3, { steps: 3 });
            await page.mouse.up();
            assert.ok(Math.abs(Number(await selection.locator('[name="left"]').inputValue()) - 10) < 1);
            assert.ok(Math.abs(Number(await selection.locator('[name="top"]').inputValue()) - 10) < 1);
            assert.ok(Math.abs(Number(await selection.locator('[name="right"]').inputValue()) - 60) < 1);
            assert.ok(Math.abs(Number(await selection.locator('[name="bottom"]').inputValue()) - 30) < 1);
            await page.locator("#pdf-zoom").selectOption("0.75");
            await page.locator('#pdf-preview[data-rendered="true"][data-zoom="0.75"]').waitFor();
            assert.ok(Math.abs(Number(await selection.locator('[name="right"]').inputValue()) - 60) < 1);
            await page.getByRole("button", { name: "Ganze ausgewählte Seite", exact: true }).click();
            assert.equal(await selection.locator('[name="right"]').inputValue(), "100");
            assert.equal(await page.getByRole("button", { name: "Freigabe beauftragen" }).count(), 0);
            await page.getByLabel("Arrangement / Ausgabe", { exact: false }).selectOption(arrangement);
            await page.getByLabel("Instrumentenvarianten", { exact: false }).selectOption(instrument);
            await page.getByLabel("Musikalische Stimmen", { exact: false }).selectOption(parts);
            await page.getByRole("button", { name: "Zuordnung speichern" }).click();
            await page.locator('#pdf-preview[data-rendered="true"]').waitFor();
            assert.equal(await page.getByRole("button", { name: "Freigabe beauftragen" }).isDisabled(), true);
            await page.reload();
            await page.locator('#pdf-preview[data-rendered="true"]').waitFor();
            assert.match(await page.locator("#inspection-state").innerText(), /Noch keine eigene/);
            await page.getByLabel("Ich habe alle Seiten", { exact: false }).check();
            await page.getByRole("button", { name: "Visuelle Prüfung speichern" }).click();
            await page.getByText("Von Ihnen für diese Version und Zuordnung visuell geprüft.", { exact: true }).waitFor();
            await page.reload();
            assert.equal(await page.getByRole("button", { name: "Freigabe beauftragen" }).isEnabled(), true);
        } else if (mode === "approve") {
            await page.getByLabel("Diese von mir visuell geprüfte", { exact: false }).check();
            await page.getByRole("button", { name: "Freigabe beauftragen" }).click();
            await page.getByText("Wartend", { exact: true }).waitFor();
        } else {
            assert.match(await page.locator("body").innerText(), /Bestätigt/);
            await page.getByRole("link", { name: "Prüfwarteschlange", exact: true }).first().click();
            assert.equal(await page.getByRole("link", { name: "Version prüfen und zuordnen" }).count(), 0);
        }
        assert.deepEqual(external, []); assert.deepEqual(errors, []);
    } finally { await browser.close(); }
}
check(process.argv[2], new URL(process.argv[3]).origin, process.argv[4], process.argv[5], process.argv[6], process.argv.slice(7))
    .catch(error => { console.error(error); process.exitCode = 1; });
