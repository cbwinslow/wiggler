import httpx


class HttpClientFactory:
    @staticmethod
    def create(user_agent: str, timeout: float = 20.0) -> httpx.AsyncClient:
        headers = {"User-Agent": user_agent}
        return httpx.AsyncClient(headers=headers, timeout=timeout, follow_redirects=True, http2=True)
