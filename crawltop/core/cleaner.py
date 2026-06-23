import trafilatura


class ContentCleaner:
    def clean(self, html: str) -> str:
        extracted = trafilatura.extract(html, include_links=False, include_images=False)
        return extracted or ""
