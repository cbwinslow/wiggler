class SearchProvider:
    async def search(self, query: str) -> list[str]:
        raise NotImplementedError


class EmbeddingProvider:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError
