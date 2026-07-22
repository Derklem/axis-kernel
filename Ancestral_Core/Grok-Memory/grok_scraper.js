// === LATTICE NEURAL INJECTOR: GROK EDITION ===
// Instructions:
// 1. Open your Grok conversation.
// 2. Press F12 to open DevTools -> Console.
// 3. Paste this entire script and hit Enter.
// 4. A file 'grok_memory_dump.json' will download automatically.

(function () {
    console.log("🔵 Anti-Gravity: Scanning Lattice...");

    function extractMetadata() {
        const messages = [];
        // Grok web interface selector heuristic
        // We look for typical chat bubble containers.
        // Update these if the structure changes.
        const potentialContainers = document.querySelectorAll('div, article, li');

        potentialContainers.forEach(container => {
            // Heuristic 1: Has meaningful text
            const text = container.innerText;
            if (!text || text.length < 5) return;

            // Heuristic 2: Look for timestamp patterns in attributes or children
            // e.g. <time>, aria-label="10:41 AM", data-timestamp
            let timestamp = "UNKNOWN";
            const timeElement = container.querySelector('time');
            if (timeElement) {
                timestamp = timeElement.getAttribute('datetime') || timeElement.innerText;
            } else {
                // Scan aria-labels for time patterns
                if (container.getAttribute('aria-label') && container.getAttribute('aria-label').match(/\d{1,2}:\d{2}/)) {
                    timestamp = container.getAttribute('aria-label');
                }
            }

            // Only capture if it looks like a distinct message (not just a wrapper)
            // This is "lossy" but captures the bulk.
            // Adjust filtering logic as needed.
            // For now, we capture *everything* text-heavy to be safe.
        });

        // FALLBACK STRATEGY: 
        // Just dump the entire text struct and we parse IT later with Python regex.
        // This is robust against DOM changes.
        return {
            url: window.location.href,
            scraped_at: new Date().toISOString(),
            raw_text: document.body.innerText,
            html_snapshot: document.body.innerHTML // We capture HTML to find hidden timestamps offline!
        };
    }

    const data = extractMetadata();

    // Create Blob
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `grok_memory_dump_${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();

    console.log("✅ Anti-Gravity: Memory extracted. Check your downloads.");
})();
