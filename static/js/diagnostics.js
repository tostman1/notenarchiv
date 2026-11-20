"use strict";

(() => {
    const panel = document.getElementById("diagnostics");
    if (!panel) return;
    const toggle = document.getElementById("live-toggle");
    const rows = document.getElementById("log-records");
    const status = document.getElementById("log-status");
    let cursor = panel.dataset.cursor;
    let running = false;
    let timer;
    let controller;
    function stop() {
        running = false;
        clearTimeout(timer);
        if (controller) controller.abort();
        toggle.textContent = panel.dataset.stopped;
        toggle.setAttribute("aria-pressed", "false");
    }
    async function poll() {
        controller = new AbortController();
        try {
            const url = new URL(panel.dataset.api, location.origin);
            if (cursor) url.searchParams.set("cursor", cursor);
            const response = await fetch(url, { credentials: "same-origin", signal: controller.signal, cache: "no-store" });
            if (!response.ok || response.redirected) throw new Error("Unavailable");
            const page = await response.json();
            if (!running) return;
            if (page.reset) {
                rows.replaceChildren();
                status.textContent = panel.dataset.reset;
            }
            for (const record of page.records) {
                const row = document.createElement("tr");
                for (const key of ["timestamp", "level", "component", "event", "job_id"]) {
                    const cell = document.createElement("td");
                    cell.textContent = record[key] || "—";
                    row.append(cell);
                }
                rows.append(row);
            }
            while (rows.children.length > 200) rows.firstElementChild.remove();
            cursor = page.cursor;
            timer = setTimeout(poll, 2000);
        } catch (error) {
            if (error.name !== "AbortError") {
                stop();
                status.textContent = panel.dataset.error;
            }
        }
    }
    toggle.addEventListener("click", () => {
        if (running) return stop();
        running = true;
        status.textContent = "";
        toggle.textContent = panel.dataset.running;
        toggle.setAttribute("aria-pressed", "true");
        poll();
    });
    window.addEventListener("pagehide", stop);
})();
