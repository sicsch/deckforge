"""PDF export wrapper around the Playwright logic in 04-pdf-export/export_to_pdf.py.

Playwright is an optional dependency (not in pyproject.toml, see issue E-04:
"nicht auf jedem Firmenlaptop installierbar"). Imports stay local to each
function so the app runs fine without it — callers must check
`is_playwright_available()` before offering the export.
"""

import functools
import tempfile
from pathlib import Path


@functools.lru_cache(maxsize=1)
def is_playwright_available() -> bool:
    """Check whether Playwright and its Chromium build are installed.

    Cached for the process lifetime — the install state doesn't change
    while the app is running, and spinning up the Playwright driver on
    every Streamlit rerun would be wasteful.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as p:
            return Path(p.chromium.executable_path).exists()
    except Exception:
        return False


def export_html_to_pdf(
    html: str, width: int = 1920, height: int = 1080, landscape: bool = True
) -> bytes:
    """Render an HTML string to PDF bytes via headless Chromium.

    Writes `html` to a temp file so Playwright can load it as `file://` —
    matches export_to_pdf.py's page setup, adapted to work on an in-memory
    deck instead of a file already on disk.
    """
    from playwright.sync_api import sync_playwright

    with tempfile.NamedTemporaryFile(
        "w", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
        f.write(html)
        html_path = Path(f.name)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": width, "height": height})
            page.goto(f"file://{html_path}")
            page.wait_for_load_state("networkidle")
            page.evaluate("document.fonts.ready")
            pdf_bytes = page.pdf(
                width=f"{width}px",
                height=f"{height}px",
                landscape=landscape,
                print_background=True,
                margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            )
            browser.close()
        return pdf_bytes
    finally:
        html_path.unlink(missing_ok=True)
