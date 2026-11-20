const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright-core");

async function check(origin) {
    const browser = await chromium.launch({ channel: process.env.BROWSER_CHANNEL || "chrome" });
    try {
        const context = await browser.newContext({ serviceWorkers: "block" });
        await context.route("**/*", route => new URL(route.request().url()).origin === origin
            ? route.continue() : route.abort());
        const page = await context.newPage();
        const label = text => new RegExp("^" + text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "\\s*:?$" );
        async function save(entity) {
            await page.getByRole("button", { name: "Speichern", exact: true }).click();
            if (await page.locator(".errorlist").count()) {
                assert.fail(await page.locator(".errorlist").allTextContents());
            }
            await page.waitForURL(new RegExp(`/catalog/${entity}/[0-9a-f-]+/$`), { timeout: 10000 });
            return new URL(page.url()).pathname.split("/")[3];
        }
        async function create(entity, values) {
            await page.goto(`${origin}/catalog/${entity}/new/`);
            for (const [name, value] of Object.entries(values)) {
                const field = page.getByLabel(label(name));
                if (typeof value === "boolean") await field.setChecked(value);
                else if (Array.isArray(value)) await field.selectOption(value[0]);
                else await field.fill(value);
            }
            return save(entity);
        }
        await page.goto(`${origin}/catalog/works/`);
        assert.equal(new URL(page.url()).pathname, "/login/");
        await page.getByLabel("Benutzername").fill("synthetic-catalog");
        await page.getByLabel("Passwort").fill("Synthetic-browser-135");
        await page.getByRole("button", { name: "Anmelden" }).click();
        const firstWork = await create("works", { Titel: "Synthetischer Marsch" });
        const secondWork = await create("works", { Titel: "Synthetischer Marsch" });
        assert.notEqual(firstWork, secondWork);
        const instrument = await create("instruments", {
            Instrument: "Synthetische Posaune", "Stimmung / Transposition": "B", "Notation / Schlüssel": ["BASS"],
        });
        const otherVariant = await create("instruments", {
            Instrument: "Synthetische Posaune", "Stimmung / Transposition": "B", "Notation / Schlüssel": ["TREBLE"],
        });
        assert.notEqual(instrument, otherVariant);
        const part = await create("parts", { Instrumentenvariante: [instrument], "Stimmennummer / Kürzel": "1" });
        const template = await create("templates", { Vorlagenname: "Synthetische Besetzung" });
        const entry = await create("template-parts", { Besetzungsvorlage: [template], Stimme: [part] });
        const arrangement = await create("arrangements", { Werk: [firstWork], "Arrangeur/in": "Synthetische Bearbeitung" });
        assert.match(await page.locator("body").innerText(), /Unbekannt: Es wurde noch keine Erwartungsliste/);
        await page.getByLabel(label("Besetzungsvorlage")).selectOption(template);
        await page.getByRole("button", { name: "Vorlage übernehmen", exact: true }).click();
        await page.getByText("Die Besetzung wurde als unabhängige Erwartungsliste übernommen.").waitFor();
        await page.goto(`${origin}/catalog/template-parts/${entry}/edit/`);
        await page.getByLabel(label("Erforderlich (sonst optional)")).uncheck();
        await save("template-parts");
        await page.goto(`${origin}/catalog/arrangements/${arrangement}/`);
        assert.match(await page.locator("body").innerText(), /Erforderlich/);
        const member = await create("members", { Name: "Synthetische Person", Stammstimme: [part] });
        const secondMember = await create("members", { Name: "Synthetische Person", Stammstimme: [part] });
        assert.notEqual(member, secondMember);
        await page.goto(`${origin}/catalog/members/${member}/edit/`);
        await page.getByLabel(label("Aktiv")).uncheck();
        await save("members");
        await page.getByText("Inaktiv", { exact: true }).waitFor();
        await page.goto(`${origin}/catalog/members/`);
        await page.getByLabel(label("Suchen")).fill("SYNTHETISCHE PERSON");
        await page.getByRole("button", { name: "Suchen", exact: true }).click();
        assert.equal(await page.locator("tbody tr").count(), 1);
        await page.getByLabel(label("Status")).selectOption("all");
        await page.getByRole("button", { name: "Suchen", exact: true }).click();
        assert.equal(await page.locator("tbody tr").count(), 2);
        if (process.env.SCREENSHOT_DIR) {
            fs.mkdirSync(process.env.SCREENSHOT_DIR, { recursive: true });
            await page.screenshot({ path: path.join(process.env.SCREENSHOT_DIR, "catalog-members-desktop.png"), fullPage: true });
        }
        await page.setViewportSize({ width: 390, height: 844 });
        const geometry = await page.evaluate(() => ({
            viewport: innerWidth, document: document.documentElement.scrollWidth,
            outside: [...document.querySelectorAll("body *")].filter(element => {
                const rect = element.getBoundingClientRect();
                const scroller = element.closest(".log-table, .catalog-tabs");
                return rect.right > innerWidth && (!scroller || scroller === element);
            }).slice(0, 15).map(element => ({
                tag: element.tagName, id: element.id, class: element.className,
                right: element.getBoundingClientRect().right, width: element.getBoundingClientRect().width,
                minWidth: getComputedStyle(element).minWidth,
            })),
        }));
        assert.ok(geometry.document <= geometry.viewport, JSON.stringify(geometry));
        if (process.env.SCREENSHOT_DIR) {
            await page.screenshot({ path: path.join(process.env.SCREENSHOT_DIR, "catalog-members-mobile.png"), fullPage: true });
        }
        await page.goto(`${origin}/catalog/parts/${part}/edit/`);
        await page.getByLabel(label("Aktiv")).uncheck();
        await page.getByRole("button", { name: "Speichern", exact: true }).click();
        assert.match((await page.locator(".errorlist").allTextContents()).join(" "), /Aktive Mitglieder verwenden/);
        await page.goto(`${origin}/catalog/parts/${part}/`);
        await page.getByText("Aktiv", { exact: true }).waitFor();
    } finally {
        await browser.close();
    }
}
check(new URL(process.argv[2]).origin).catch(error => {
    console.error(error);
    process.exitCode = 1;
});
