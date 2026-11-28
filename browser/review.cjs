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
        } else if (mode === "merge") {
            await page.getByText("Zwei angrenzende Regionen ausdrücklich vereinigen", { exact: true }).click();
            const merge = page.locator('#region-merge');
            const children = await merge.locator('select[name="first_region"] option').evaluateAll(options =>
                options.filter(option => /Version 1$/.test(option.textContent.trim())).map(option => option.value));
            assert.equal(children.length, 2);
            await merge.locator('[name="first_region"]').selectOption(children[0]);
            await merge.locator('[name="second_region"]').selectOption(children[1]);
            await merge.locator('[name="merge_acknowledged"]').check();
            await merge.locator('button').click();
            await page.getByText("Neue vereinigte Region gespeichert – bisherige Regionen unverändert.", { exact: true }).waitFor();
            await page.locator('[data-region-number="1"]').nth(2).waitFor({ state: "attached", timeout: 15000 });
            await page.locator('[data-region-number="2"]').waitFor({ state: "attached", timeout: 15000 });
            assert.equal(await page.locator('[data-region-number="1"]').count(), 3);
            assert.equal(await page.locator('[data-region-number="2"]').count(), 1);
        } else if (mode === "split") {
            const selection = page.locator("#ocr-selection");
            for (const [name, value] of Object.entries({ page: "2", left: "10", top: "20", right: "80", bottom: "90" })) {
                await selection.locator(`[name="${name}"]`).fill(value);
            }
            await page.locator('#pdf-preview[data-rendered="true"][data-page="2"]').waitFor();
            await page.getByText("Ausgewählten Bereich ausdrücklich in zwei neue Bereiche teilen", { exact: true }).click();
            await selection.locator('[name="split_axis"]').selectOption("vertical");
            await selection.locator('[name="split_percent"]').fill("50");
            await selection.locator('[name="split_acknowledged"]').check();
            await page.getByRole("button", { name: "Zwei neue unbestätigte Bereiche speichern", exact: true }).click();
            await page.getByText("Zwei neue Bereiche gespeichert – bestehende Bereiche und Freigaben unverändert.", { exact: true }).waitFor();
            assert.equal(await page.locator('[data-region-number="1"]').count(), 2);
            assert.equal(await page.locator('[data-region-number="2"]').count(), 1);
        } else if (mode === "content-review") {
            // Settle the unrelated lazy image before requesting the pinned PDF;
            // both deliberately use the same nonblocking native preview slot.
            const sourceImage = page.locator('img[src*="/ocr/"]');
            await sourceImage.scrollIntoViewIfNeeded();
            await sourceImage.evaluate(element => element.decode());
            assert.ok(await sourceImage.evaluate(element => element.naturalWidth > 0));
            await page.getByRole("link", { name: "Inhaltsvorschlag ansehen – Revision 1", exact: true }).click();
            await page.locator('#pdf-preview[data-rendered="true"]').waitFor();
            assert.equal(await page.locator('#pdf-count').textContent(), "2");
            await page.locator('#pdf-next').click();
            await page.locator('#pdf-preview[data-rendered="true"][data-page="2"]').waitFor();
            await page.getByLabel("Ich habe jedes Vorkommen dieser gespeicherten Folge einschließlich Fortsetzungen visuell geprüft.", { exact: true }).check();
            await page.getByRole("button", { name: "Diese Inhaltsrevision als visuell geprüft bestätigen", exact: true }).click();
            await page.getByText("Sichtprüfung dieser Inhaltsrevision gespeichert; noch keine musikalische Freigabe.", { exact: true }).waitFor();
            await page.getByLabel("Ich gebe genau diese geprüfte Inhaltsrevision für neue musikalische Verwendung frei.", { exact: true }).check();
            await page.getByRole("button", { name: "Diese geprüfte Inhaltsrevision musikalisch freigeben", exact: true }).click();
            await page.getByText("Genau diese geprüfte Inhaltsrevision ist musikalisch freigegeben.", { exact: true }).waitFor();
        } else if (mode === "content") {
            await page.getByText("Neue musikalische Inhaltsausgabe anlegen", { exact: true }).click();
            const creation = page.locator('form:has(input[value="content_edition_create"])');
            await creation.locator('[name="arrangement"]').selectOption(arrangement);
            await creation.locator('[name="part"]').selectOption(parts[0]);
            await creation.locator('[name="explicit"]').check();
            await creation.locator('button').click();
            await page.getByText("Regionsfolge als musikalischen Inhaltsvorschlag speichern", { exact: true }).click();
            const content = page.locator('form:has(input[value="region_content"])');
            await content.locator('[name="edition"]').selectOption({ index: 1 });
            await content.locator('[name="expected_edition_number"]').fill("0");
            const revision = await content.locator('select[name="region"]').first().locator('option').nth(1).getAttribute('value');
            await content.locator('select[name="region"]').nth(0).selectOption(revision);
            await content.locator('select[name="region"]').nth(1).selectOption(revision);
            await content.locator('button').click();
            await page.getByText("Inhaltsvorschlag gespeichert – noch nicht inspiziert oder freigegeben.", { exact: true }).waitFor();
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
            // Settle the lazy OCR render before requesting another
            // native preview: the application deliberately has one nonblocking slot.
            const precedingImage = page.locator('img[src*="/ocr/"]');
            await precedingImage.scrollIntoViewIfNeeded();
            await precedingImage.evaluate(element => element.decode());
            assert.ok(await precedingImage.evaluate(element => element.naturalWidth > 0));
            await page.getByText("Unbestätigten Regionsauszug ansehen", { exact: false }).click();
            const regionImage = page.locator('img[src*="/region/"]');
            await regionImage.scrollIntoViewIfNeeded();
            await regionImage.evaluate(element => element.decode());
            assert.ok(await regionImage.evaluate(element => element.naturalWidth > 0));
            const sequence = page.locator('form[action$="/regions/"]');
            const revision = await sequence.locator('select').first().locator('option').nth(1).getAttribute('value');
            await sequence.locator('select').nth(0).selectOption(revision);
            await sequence.locator('select').nth(1).selectOption(revision);
            await page.getByRole('button', { name: 'Unbestätigte Folge vorschauen', exact: true }).click();
            await page.locator('#pdf-preview[data-rendered="true"]').waitFor();
            assert.equal(await page.locator('#pdf-count').innerText(), '2');
            await page.getByRole('link', { name: 'Zurück zur Quellprüfung', exact: true }).click();
            await page.locator('#pdf-preview[data-rendered="true"]').waitFor();
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
            const correction = page.locator('form').filter({ has: page.locator('input[name="action"][value="save"]') });
            await correction.getByLabel("Arrangement / Ausgabe", { exact: false }).selectOption(arrangement);
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
