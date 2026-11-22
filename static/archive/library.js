// Local-only progressive enhancement; GET works without JavaScript.
(() => {
    const form = document.querySelector('#library-search');
    if (!form) return;
    let timer, controller, sequence = 0;
    async function update() {
        controller?.abort(); controller = new AbortController();
        const current = ++sequence;
        const url = new URL(form.action || location.href);
        url.search = new URLSearchParams(new FormData(form)).toString();
        try {
            const response = await fetch(url, { signal: controller.signal, credentials: 'same-origin' });
            if (!response.ok) return;
            const document = new DOMParser().parseFromString(await response.text(), 'text/html');
            const results = document.querySelector('#library-results');
            if (current !== sequence || !results) return;
            window.document.querySelector('#library-results').replaceWith(results);
            history.replaceState(null, '', url);
        } catch (error) { if (error.name !== 'AbortError') return; }
    }
    form.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(update, 250); });
    form.addEventListener('change', () => { clearTimeout(timer); update(); });
})();
