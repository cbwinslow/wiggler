from dataclasses import dataclass


@dataclass(slots=True)
class AgentResult:
    name: str
    output: str
    confidence: float | None = None


class Agent:
    name = "base"

    async def run(self, text: str) -> AgentResult:
        return AgentResult(name=self.name, output=text, confidence=None)
