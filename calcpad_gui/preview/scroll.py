"""Historical output scroll-restoration injection, independent of GTK."""
def inject_output_scroll_restore(html: str) -> str:
    """Keep WebKit preview scroll position stable across HTML reloads."""
    script = r"""
<script id="calcpad-scroll-restore">
(function () {
    const markerY = "calcpadScrollY=";
    const markerRatio = "calcpadScrollRatio=";

    function getScrollElement() {
        return document.scrollingElement || document.documentElement || document.body;
    }

    function getMaxScroll(el) {
        if (!el) return 0;
        return Math.max(0, el.scrollHeight - el.clientHeight);
    }

    function readValue(marker) {
        const name = String(window.name || "");
        const idx = name.indexOf(marker);
        if (idx < 0) return 0;

        const raw = name.slice(idx + marker.length).split(";")[0];
        const value = parseFloat(raw);

        return Number.isFinite(value) ? value : 0;
    }

    function writeValue(marker, value) {
        let name = String(window.name || "");
        const escaped = marker.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        name = name.replace(new RegExp(";?" + escaped + "[0-9.]+", "g"), "");
        window.name = name + ";" + marker + String(Math.max(0, value || 0));
    }

    function save() {
        const el = getScrollElement();
        if (!el) return;

        const y = el.scrollTop || window.scrollY || 0;
        const max = getMaxScroll(el);
        const ratio = max > 0 ? y / max : 0;

        writeValue(markerY, y);
        writeValue(markerRatio, ratio);
    }

    function restore() {
        const el = getScrollElement();
        if (!el) return;

        const savedY = readValue(markerY);
        const savedRatio = readValue(markerRatio);
        const max = getMaxScroll(el);

        let targetY = savedY;

        if (max > 0 && savedRatio > 0) {
            targetY = Math.min(savedY, max);
            if (savedY > max) {
                targetY = max * savedRatio;
            }
        }

        if (!targetY) return;

        function apply() {
            window.scrollTo(0, targetY);
            el.scrollTop = targetY;
        }

        apply();
        setTimeout(apply, 50);
        setTimeout(apply, 150);
        setTimeout(apply, 350);
        setTimeout(apply, 700);
    }

    window.addEventListener("scroll", save, { passive: true });
    window.addEventListener("beforeunload", save);
    window.addEventListener("DOMContentLoaded", restore);
    window.addEventListener("load", restore);
})();
</script>
"""

    if 'id="calcpad-scroll-restore"' in html:
        return html

    lower = html.lower()
    body_idx = lower.rfind("</body>")

    if body_idx >= 0:
        return html[:body_idx] + script + html[body_idx:]

    return html + script
