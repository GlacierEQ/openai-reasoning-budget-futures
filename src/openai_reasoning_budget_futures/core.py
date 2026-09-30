"""ML Inference Optimization & KV-Cache Management — Core Module"""

import math
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class KVCacheConfig:
    """Configuration for KV-cache memory management."""
    num_layers: int
    num_heads: int
    head_dim: int
    max_seq_len: int
    dtype_bytes: int = 2  # fp16 = 2, int8 = 1, int4 = 0.5

    @property
    def bytes_per_token(self) -> int:
        """Memory per token per KV pair: 2 * layers * heads * dim * dtype."""
        return 2 * self.num_layers * self.num_heads * self.head_dim * self.dtype_bytes

    @property
    def max_cache_bytes(self) -> int:
        return self.bytes_per_token * self.max_seq_len

    @property
    def max_cache_gb(self) -> float:
        return self.max_cache_bytes / (1024 ** 3)

    def tokens_fitting_budget(self, budget_gb: float) -> int:
        """How many tokens fit in a given memory budget."""
        budget_bytes = budget_gb * (1024 ** 3)
        return int(budget_bytes / self.bytes_per_token)


@dataclass
class ReasoningBudget:
    """Token budget allocation for chain-of-thought reasoning."""
    max_reasoning_tokens: int
    max_output_tokens: int
    cost_per_input_token: float   # dollars
    cost_per_output_token: float

    def total_cost(self, input_tokens: int) -> float:
        """Worst-case cost for a reasoning request."""
        return (
            input_tokens * self.cost_per_input_token
            + self.max_reasoning_tokens * self.cost_per_output_token
            + self.max_output_tokens * self.cost_per_output_token
        )

    def cost_ratio(self, input_tokens: int) -> float:
        """Ratio of reasoning cost to output cost."""
        reasoning_cost = self.max_reasoning_tokens * self.cost_per_output_token
        output_cost = self.max_output_tokens * self.cost_per_output_token
        return reasoning_cost / output_cost if output_cost > 0 else float('inf')


class QuantizationPlanner:
    """Plans quantization strategy to fit KV-cache in hardware budget."""

    DTYPE_MAP = {"fp32": 4, "fp16": 2, "bf16": 2, "int8": 1, "int4": 0.5}

    @classmethod
    def plan(cls, config: KVCacheConfig, target_gb: float) -> Optional[str]:
        """Find the highest precision dtype that fits the target budget."""
        for dtype_name, nbytes in sorted(cls.DTYPE_MAP.items(), key=lambda x: -x[1]):
            test = KVCacheConfig(
                config.num_layers, config.num_heads,
                config.head_dim, config.max_seq_len, int(nbytes)
            )
            if test.max_cache_gb <= target_gb:
                return dtype_name
        return None

    @classmethod
    def compression_ratio(cls, from_dtype: str, to_dtype: str) -> float:
        return cls.DTYPE_MAP[from_dtype] / cls.DTYPE_MAP[to_dtype]

