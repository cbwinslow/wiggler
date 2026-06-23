from selectolax.parser import HTMLParser


class ParsedPage:
    def __init__(self, title: str | None, text: str, links: list[str]):
        self.title = title
        self.text = text
        self.links = links


class HtmlParser:
    def parse(self, html: str, base_url: str) -> ParsedPage:
        tree = HTMLParser(html)
        title = tree.css_first("title")
        links = []
        for node in tree.css("a"):
            href = node.attributes.get("href")
            if href:
                links.append(href)
        text = tree.body.text(separator=" ", strip=True) if tree.body else ""
        return ParsedPage(title.text(strip=True) if title else None, text, links)
