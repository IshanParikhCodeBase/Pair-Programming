"""Claude Haiku 4.5 prices and cost math.

Single source of truth for pricing — every chart and results-table row computes
cost by calling `cost()` here, so a price update is a one-line change.

Prices confirmed at time of writing (see lab brief, Sec. 3). Per million tokens.
"""

from dataclasses import dataclass

INPUT_PRICE_PER_MTOK = 1.00
OUTPUT_PRICE_PER_MTOK = 5.00
CACHE_READ_PRICE_PER_MTOK = 0.10
CACHE_WRITE_PRICE_PER_MTOK = 1.25


@dataclass
class Cost:
    input_cost: float
    output_cost: float
    cache_read_cost: float

    @property
    def total(self):
        return self.input_cost + self.output_cost + self.cache_read_cost


def cost(input_tokens, output_tokens, cache_read_tokens=0):
    """Cost of one request. `cache_read_tokens` is a subset of input_tokens that
    was served from the prompt cache instead of priced at the full input rate —
    pass 0 (default) when no caching is in play.
    """
    billed_input_tokens = input_tokens - cache_read_tokens
    return Cost(
        input_cost=billed_input_tokens * INPUT_PRICE_PER_MTOK / 1_000_000,
        output_cost=output_tokens * OUTPUT_PRICE_PER_MTOK / 1_000_000,
        cache_read_cost=cache_read_tokens * CACHE_READ_PRICE_PER_MTOK / 1_000_000,
    )


def approx_token_count(text):
    """Fast, deterministic, fully-offline token estimate for the mock model.

    Not exact — real counts for the real model come from the API response's
    `usage` field instead. This is only ever used for mock-model development
    numbers, never for a number that lands in the results table.
    """
    return max(1, len(text) // 4)
