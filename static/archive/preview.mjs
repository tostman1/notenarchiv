import { getDocument, GlobalWorkerOptions } from "../vendor/pdfjs/build/pdf.mjs";

const root = document.getElementById("pdf-preview");
const canvas = document.getElementById("pdf-canvas");
const status = document.getElementById("pdf-status");
const pageInput = document.getElementById("pdf-page");
const zoom = document.getElementById("pdf-zoom");
const previous = document.getElementById("pdf-previous");
const next = document.getElementById("pdf-next");
let pdf, current = 1, rendering = false, requested = false;
let loadingTask;
const selection = document.getElementById("ocr-selection");
const regionButtons = [...document.querySelectorAll("[data-region-id]")];
let overlay, drawing = false, start;
const selectionFields = selection && Object.fromEntries(
    ["page", "left", "top", "right", "bottom"].map(name => [name, selection.elements.namedItem(name)])
);

function paintSelection() {
    if (!overlay) return;
    overlay.width = canvas.width;
    overlay.height = canvas.height;
    const context = overlay.getContext("2d");
    if (Number(selectionFields.page.value) !== Number(root.dataset.page)) return;
    const values = ["left", "top", "right", "bottom"].map(name => Number(selectionFields[name].value));
    if (!values.every(value => Number.isFinite(value) && value >= 0 && value <= 100)) return;
    const [left, top, right, bottom] = values;
    if (left >= right || top >= bottom) return;
    context.strokeStyle = "#0057b8";
    context.lineWidth = 3;
    context.fillStyle = "rgba(0, 87, 184, 0.12)";
    const rectangle = [left * overlay.width / 100, top * overlay.height / 100,
        (right - left) * overlay.width / 100, (bottom - top) * overlay.height / 100];
    context.fillRect(...rectangle);
    context.strokeRect(...rectangle);
}

if (selection) {
    const wrapper = document.createElement("div");
    wrapper.className = "ocr-canvas-stack";
    canvas.before(wrapper);
    wrapper.append(canvas);
    overlay = document.createElement("canvas");
    overlay.className = "ocr-selection-overlay";
    overlay.setAttribute("aria-hidden", "true");
    wrapper.append(overlay);
    selection.addEventListener("input", paintSelection);
    document.getElementById("region-new")?.addEventListener("click", () => {
        selection.elements.namedItem("region_id").value = "";
        selection.elements.namedItem("expected_region_number").value = "0";
    });
    regionButtons.forEach(button => {
        button.addEventListener("click", () => {
            if (!pdf || rendering || root.dataset.rendered !== "true") return;
            selection.elements.namedItem("region_id").value = button.dataset.regionId;
            selection.elements.namedItem("expected_region_number").value = button.dataset.regionNumber;
            for (const name of ["page", "left", "top", "right", "bottom"]) {
                selectionFields[name].value = button.dataset["region" + name[0].toUpperCase() + name.slice(1)];
            }
            selectionFields.page.dispatchEvent(new Event("change"));
            paintSelection();
        });
    });
    selectionFields.page.addEventListener("change", () => {
        const value = Number(selectionFields.page.value);
        if (pdf && Number.isInteger(value) && value >= 1 && value <= pdf.numPages) {
            current = value;
            renderPage();
        }
    });
    document.getElementById("ocr-draw").addEventListener("click", () => {
        if (root.dataset.rendered !== "true") return;
        drawing = !drawing;
        overlay.classList.toggle("drawing", drawing);
        document.getElementById("ocr-draw").setAttribute("aria-pressed", String(drawing));
    });
    document.getElementById("ocr-reset").addEventListener("click", () => {
        for (const name of ["left", "top"]) selectionFields[name].value = 0;
        for (const name of ["right", "bottom"]) selectionFields[name].value = 100;
        paintSelection();
    });
    const point = event => {
        const box = overlay.getBoundingClientRect();
        return [Math.min(100, Math.max(0, (event.clientX - box.left) / box.width * 100)),
            Math.min(100, Math.max(0, (event.clientY - box.top) / box.height * 100))];
    };
    overlay.addEventListener("pointerdown", event => {
        if (!drawing || rendering || event.button !== 0) return;
        selectionFields.page.value = root.dataset.page;
        start = point(event);
        overlay.setPointerCapture(event.pointerId);
        event.preventDefault();
    });
    overlay.addEventListener("pointermove", event => {
        if (!start) return;
        const end = point(event);
        ["left", "top", "right", "bottom"].forEach((name, index) => {
            selectionFields[name].value = [Math.min(start[0], end[0]), Math.min(start[1], end[1]),
                Math.max(start[0], end[0]), Math.max(start[1], end[1])][index].toFixed(3);
        });
        paintSelection();
    });
    const stop = () => { start = undefined; };
    overlay.addEventListener("pointerup", stop);
    overlay.addEventListener("pointercancel", stop);
    overlay.addEventListener("lostpointercapture", stop);
}
GlobalWorkerOptions.workerSrc = root.dataset.workerUrl;

function fail() {
    root.dataset.rendered = "false";
    regionButtons.forEach(button => { button.disabled = true; });
    status.textContent = root.dataset.error;
    status.setAttribute("role", "alert");
    for (const control of [pageInput, zoom, previous, next]) control.disabled = true;
    canvas.width = canvas.height = 0;
    if (overlay) overlay.width = overlay.height = 0;
    pdf?.destroy();
}

async function renderPage() {
    requested = true;
    if (rendering) return;
    rendering = true;
    regionButtons.forEach(button => { button.disabled = true; });
    try {
        while (requested) {
            requested = false;
            root.dataset.rendered = "false";
            status.textContent = root.dataset.loading;
            const number = current;
            const page = await pdf.getPage(number);
            const viewport = page.getViewport({ scale: Number(zoom.value) });
            // Bound canvas memory even for hostile geometry/high DPI displays.
            if (!Number.isFinite(viewport.width * viewport.height) ||
                viewport.width * viewport.height > 16_000_000 ||
                Math.max(viewport.width, viewport.height) > 8192) throw new Error("limit");
            canvas.width = Math.ceil(viewport.width);
            canvas.height = Math.ceil(viewport.height);
            await page.render({ canvasContext: canvas.getContext("2d"), viewport }).promise;
            page.cleanup();
            pageInput.value = number;
            previous.disabled = number === 1;
            next.disabled = number === pdf.numPages;
            status.textContent = root.dataset.ready;
            root.dataset.rendered = "true";
            root.dataset.page = String(number);
            root.dataset.zoom = zoom.value;
            if (selection) {
                selectionFields.page.value = number;
                paintSelection();
            }
        }
    } catch { fail(); } finally {
        rendering = false;
        if (root.dataset.rendered === "true") regionButtons.forEach(button => { button.disabled = false; });
    }
}

previous.addEventListener("click", () => { if (current > 1) { current--; renderPage(); } });
next.addEventListener("click", () => { if (current < pdf.numPages) { current++; renderPage(); } });
pageInput.addEventListener("change", () => {
    const value = Number(pageInput.value);
    if (Number.isInteger(value) && value >= 1 && value <= pdf.numPages) current = value;
    else pageInput.value = current;
    renderPage();
});
zoom.addEventListener("change", renderPage);
document.querySelectorAll("[data-preview-page]").forEach(button => {
    button.addEventListener("click", () => {
        const value = Number(button.dataset.previewPage);
        if (pdf && Number.isInteger(value) && value >= 1 && value <= pdf.numPages) {
            current = value;
            renderPage();
        }
    });
});

try {
    const response = await fetch(root.dataset.documentUrl, { credentials: "same-origin", redirect: "error", cache: "no-store" });
    if (!response.ok || response.headers.get("content-type") !== "application/pdf") throw new Error("unavailable");
    loadingTask = getDocument({
        data: new Uint8Array(await response.arrayBuffer()),
        isEvalSupported: false,
        enableXfa: false,
        useWasm: false,
        disableAutoFetch: true,
        disableRange: true,
        disableStream: true,
        cMapUrl: root.dataset.assetsUrl + "cmaps/",
        cMapPacked: true,
        standardFontDataUrl: root.dataset.assetsUrl + "standard_fonts/",
        useWorkerFetch: true,
        maxImageSize: 16_000_000,
        canvasMaxAreaInBytes: 64_000_000,
    });
    // No scripting manager, annotation/link/form layer, attachments, external
    // actions, document metadata DOM injection or download/print UI is installed.
    pdf = await loadingTask.promise;
    if (pdf.numPages > 500) throw new Error("limit");
    document.getElementById("pdf-count").textContent = pdf.numPages;
    pageInput.max = pdf.numPages;
    if (selection) selectionFields.page.max = pdf.numPages;
    pageInput.disabled = zoom.disabled = false;
    await renderPage();
} catch { loadingTask?.destroy(); fail(); }
window.addEventListener("pagehide", () => { loadingTask?.destroy(); });
