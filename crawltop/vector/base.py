class VectorIndex:
    async def upsert(self, items: list[dict]) -> None:
        raise NotImplementedError

    async def search(self, query_vector: list[float], limit: int = 5) -> list[dict]:
        raise NotImplementedError
