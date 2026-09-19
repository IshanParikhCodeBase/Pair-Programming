"""The model 'socket': one interface, two plugs (MockModel, ClaudeHaikuModel).

Every caller in this lab talks to a ModelClient through `generate(system,
user_message)` and gets back a ModelResponse with the answer text plus exactly
the input/output token counts that determine cost. Swapping which subclass is
plugged in must never require touching retrieval/pipeline code.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

import anthropic

from . import config
from .tokens import approx_token_count, cost, Cost


@dataclass
class ModelResponse:
    text: str
    input_tokens: int
    output_tokens: int
    cost: Cost


class ModelClient(ABC):
    @abstractmethod
    def generate(self, system: str, user_message: str) -> ModelResponse:
        ...


class MockModel(ModelClient):
    """Offline, free, deterministic. Not an LLM — a keyword-overlap stand-in
    used only to exercise the plumbing (prompt formatting, token counting,
    cost math, logging) while we build the pipeline. Never the source of a
    number that lands in the results table.
    """

    name = "mock"

    def generate(self, system: str, user_message: str) -> ModelResponse:
        question = _extract_question(user_message)
        answer = _most_overlapping_sentence(user_message, question)
        input_tokens = approx_token_count(system) + approx_token_count(user_message)
        output_tokens = approx_token_count(answer)
        return ModelResponse(
            text=answer,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost(input_tokens, output_tokens),
        )


class ClaudeHaikuModel(ModelClient):
    """Real Claude Haiku 4.5 via the Anthropic API. Token counts come straight
    from the API response's `usage` field, so they match actual billing.
    """

    name = "claude-haiku-4-5"

    def __init__(self, model_name: str = config.HAIKU_MODEL_NAME, max_tokens: int = 1024):
        self.client = anthropic.Anthropic()
        self.model_name = model_name
        self.max_tokens = max_tokens

    def generate(self, system: str, user_message: str) -> ModelResponse:
        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return ModelResponse(
            text=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cost=cost(response.usage.input_tokens, response.usage.output_tokens),
        )


def get_model(name: str) -> ModelClient:
    if name == "mock":
        return MockModel()
    if name in ("haiku", "claude-haiku-4-5"):
        return ClaudeHaikuModel()
    raise ValueError(f"Unknown model: {name!r}")


_WORD_RE = re.compile(r"[a-z0-9]+")


def _extract_question(user_message: str) -> str:
    match = re.search(r"Question:\s*(.+)", user_message)
    return match.group(1).strip() if match else user_message.strip().splitlines()[-1]


def _most_overlapping_sentence(context: str, question: str) -> str:
    q_words = set(_WORD_RE.findall(question.lower()))
    context = context[: context.rfind("Question:")] if "Question:" in context else context
    sentences = re.split(r"(?<=[.!?])\s+|\n+", context)
    best, best_score = "", -1
    for sentence in sentences:
        if not sentence.strip():
            continue
        s_words = set(_WORD_RE.findall(sentence.lower()))
        score = len(q_words & s_words)
        if score > best_score:
            best, best_score = sentence.strip(), score
    return best or "I don't know."


if __name__ == "__main__":
    # Connection smoke test: `python -m contextlab.model_client` (run from src/,
    # with the venv active) — confirms the API key works and a real Haiku 4.5
    # response comes back, before we wire this into anything else.
    print(f"Connecting to {config.HAIKU_MODEL_NAME} ...")
    model = ClaudeHaikuModel()
    question = "What is capital of India?"
    response = model.generate(
        system="You are a helpful, concise assistant.",
        user_message=f"Question: {question}",
    )
    print(f"Question: {question}")
    print(f"Answer:   {response.text}")
    print(f"Input tokens:  {response.input_tokens}")
    print(f"Output tokens: {response.output_tokens}")
    print(f"Cost: ${response.cost.total:.6f}  "
          f"(input ${response.cost.input_cost:.6f} + output ${response.cost.output_cost:.6f})")
