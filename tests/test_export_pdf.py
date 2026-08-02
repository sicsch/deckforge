from app.export import pdf


def test_is_playwright_available_false_when_not_installed():
    """Dev/CI envs don't install Playwright (optional dep, see issue E-04) —
    this exercises the real ImportError path, not a mock.
    """
    pdf.is_playwright_available.cache_clear()

    assert pdf.is_playwright_available() is False


def test_export_html_to_pdf_raises_when_playwright_missing():
    try:
        pdf.export_html_to_pdf("<html></html>")
    except ImportError:
        pass
    else:
        raise AssertionError("expected ImportError when playwright isn't installed")
