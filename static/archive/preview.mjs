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
GlobalWorkerOptions.workerSrc = root.dataset.workerUrl;

function fail() {
    status.textContent = root.dataset.error;
    status.setAttribute("role", "alert");
    for (const control of [pageInput, zoom, previous, next]) control.disabled = true;
    canvas.width = canvas.height = 0;
    pdf?.destroy();
}

async function renderPage() {
    requested = true;
    if (rendering) return;
    rendering = true;
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
        }
    } catch { fail(); } finally { rendering = false; }
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
    pageInput.disabled = zoom.disabled = false;
    await renderPage();
} catch { loadingTask?.destroy(); fail(); }
window.addEventListener("pagehide", () => { loadingTask?.destroy(); });
