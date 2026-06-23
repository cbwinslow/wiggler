from crawltop.config import get_settings
from crawltop.tui.dashboard import CrawlTopApp


def run() -> None:
    settings = get_settings()
    app = CrawlTopApp(settings)
    app.run()


if __name__ == "__main__":
    run()
