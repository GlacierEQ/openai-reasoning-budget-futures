"""Portfolio allocator for reasoning-budget futures.

This module composes the repository's fail-closed single-future ledger into a
multi-job planning surface. Utility and uncertainty are caller-declared planning
inputs, not measured model quality. Pareto dominance is primary: real tradeoffs
remain visible before a preference chooses among non-dominated allocations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from math import isfinite
from typing import Iterable, Literal

from .budget_futures import ReasoningBudgetLedger

EVIDENCE_STATE = "DETERMINISTIC_REASONING_PORTFOLIO_MODEL"
Preference = Literal["balanced", "value", "efficiency", "risk"]


class PortfolioTooLarge(ValueError):
    """Raised when an allocation search would exceed the declared search ceiling."""


class NoFeasibleAllocation(ValueError):
    """Raised when mandatory work cannot fit inside the declared resource pool."""


@dataclass(frozen=True)
class ReasoningTier:
    name: str
    tokens: int
    tool_calls: int
    parallel_agents: int
    utility: float
    uncertainty: float = 0.0

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("tier name must be non-empty")
        for name in ("tokens", "tool_calls", "parallel_agents"):
            value = getattr(self, name)
            if value < 1:
                raise ValueError(f"{name} must be positive")
        for name in ("utility", "uncertainty"):
            value = getattr(self, name)
            if not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and non-negative")


@dataclass(frozen=True)
class ReasoningBid:
    job_id: str
    tiers: tuple[ReasoningTier, ...]
    required: bool = False

    def __post_init__(self) -> None:
        if not self.job_id.strip():
            raise ValueError("job_id must be non-empty")
        if not self.tiers:
            raise ValueError("each bid requires at least one tier")
        names = [tier.name for tier in self.tiers]
        if len(names) != len(set(names)):
            raise ValueError("tier names must be unique within a bid")


@dataclass(frozen=True)
class ResourcePool:
    tokens: int
    tool_calls: int
    parallel_agents: int
    max_combinations: int = 100_000

    def __post_init__(self) -> None:
        for name in ("tokens", "tool_calls", "parallel_agents", "max_combinations"):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be positive")


@dataclass(frozen=True)
class AllocationChoice:
    job_id: str
    tier: ReasoningTier

    def to_dict(self) -> dict[str, object]:
        return {"job_id": self.job_id, "tier": asdict(self.tier)}


@dataclass(frozen=True)
class ReasoningAllocation:
    choices: tuple[AllocationChoice, ...]
    total_tokens: int
    total_tool_calls: int
    total_parallel_agents: int
    total_utility: float
    total_uncertainty: float
    evidence_state: str = EVIDENCE_STATE

    @property
    def jobs_run(self) -> int:
        return len(self.choices)

    @property
    def utility_per_1k_tokens(self) -> float:
        if self.total_tokens == 0:
            return 0.0
        return self.total_utility / (self.total_tokens / 1000.0)

    def dominates(self, other: "ReasoningAllocation") -> bool:
        """Return true when this allocation is Pareto-superior to another."""

        gains_mine = (self.total_utility, self.jobs_run)
        gains_other = (other.total_utility, other.jobs_run)
        costs_mine = (
            self.total_tokens,
            self.total_tool_calls,
            self.total_parallel_agents,
            self.total_uncertainty,
        )
        costs_other = (
            other.total_tokens,
            other.total_tool_calls,
            other.total_parallel_agents,
            other.total_uncertainty,
        )
        no_worse = all(left >= right for left, right in zip(gains_mine, gains_other))
        no_worse = no_worse and all(
            left <= right for left, right in zip(costs_mine, costs_other)
        )
        strictly_better = any(
            left > right for left, right in zip(gains_mine, gains_other)
        ) or any(left < right for left, right in zip(costs_mine, costs_other))
        return no_worse and strictly_better

    def to_dict(self) -> dict[str, object]:
        return {
            "choices": [choice.to_dict() for choice in self.choices],
            "jobs_run": self.jobs_run,
            "total_tokens": self.total_tokens,
            "total_tool_calls": self.total_tool_calls,
            "total_parallel_agents": self.total_parallel_agents,
            "total_utility": round(self.total_utility, 6),
            "total_uncertainty": round(self.total_uncertainty, 6),
            "utility_per_1k_tokens": round(self.utility_per_1k_tokens, 6),
            "evidence_state": self.evidence_state,
        }


class ReasoningFuturesExchange:
    """Enumerate feasible portfolios, preserve the Pareto frontier, then select."""

    def __init__(self, bids: Iterable[ReasoningBid], pool: ResourcePool) -> None:
        self.bids = tuple(bids)
        self.pool = pool
        if not self.bids:
            raise ValueError("at least one reasoning bid is required")
        ids = [bid.job_id for bid in self.bids]
        if len(ids) != len(set(ids)):
            raise ValueError("job_id values must be unique")

    @property
    def combination_count(self) -> int:
        count = 1
        for bid in self.bids:
            count *= len(bid.tiers) if bid.required else len(bid.tiers) + 1
        return count

    def _guard_search_size(self) -> None:
        if self.combination_count > self.pool.max_combinations:
            raise PortfolioTooLarge(
                f"allocation search requires {self.combination_count} combinations; "
                f"ceiling is {self.pool.max_combinations}"
            )

    def feasible_allocations(self) -> list[ReasoningAllocation]:
        self._guard_search_size()
        option_sets = [
            bid.tiers if bid.required else (None, *bid.tiers)
            for bid in self.bids
        ]
        feasible: list[ReasoningAllocation] = []
        for selected in product(*option_sets):
            choices = tuple(
                AllocationChoice(bid.job_id, tier)
                for bid, tier in zip(self.bids, selected)
                if tier is not None
            )
            total_tokens = sum(choice.tier.tokens for choice in choices)
            total_tools = sum(choice.tier.tool_calls for choice in choices)
            total_agents = sum(choice.tier.parallel_agents for choice in choices)
            if (
                total_tokens > self.pool.tokens
                or total_tools > self.pool.tool_calls
                or total_agents > self.pool.parallel_agents
            ):
                continue
            feasible.append(
                ReasoningAllocation(
                    choices=choices,
                    total_tokens=total_tokens,
                    total_tool_calls=total_tools,
                    total_parallel_agents=total_agents,
                    total_utility=sum(choice.tier.utility for choice in choices),
                    total_uncertainty=sum(choice.tier.uncertainty for choice in choices),
                )
            )

        if not feasible:
            required = [bid.job_id for bid in self.bids if bid.required]
            raise NoFeasibleAllocation(
                "no portfolio satisfies resource capacity"
                + (f" for mandatory jobs {required}" if required else "")
            )
        return feasible

    @staticmethod
    def pareto_frontier(
        allocations: Iterable[ReasoningAllocation],
    ) -> list[ReasoningAllocation]:
        items = list(allocations)
        frontier = [
            candidate
            for candidate in items
            if not any(
                other.dominates(candidate)
                for other in items
                if other is not candidate
            )
        ]
        return sorted(
            frontier,
            key=lambda item: (
                -item.total_utility,
                -item.jobs_run,
                item.total_uncertainty,
                item.total_tokens,
            ),
        )

    def frontier(self) -> list[ReasoningAllocation]:
        return self.pareto_frontier(self.feasible_allocations())

    def select(self, preference: Preference = "balanced") -> ReasoningAllocation:
        frontier = self.frontier()
        if preference not in {"balanced", "value", "efficiency", "risk"}:
            raise ValueError("preference must be balanced, value, efficiency, or risk")
        if preference == "value":
            return max(
                frontier,
                key=lambda item: (
                    item.total_utility,
                    item.jobs_run,
                    -item.total_uncertainty,
                    -item.total_tokens,
                ),
            )
        if preference == "efficiency":
            return max(
                frontier,
                key=lambda item: (
                    item.utility_per_1k_tokens,
                    item.total_utility,
                    -item.total_uncertainty,
                ),
            )
        if preference == "risk":
            return min(
                frontier,
                key=lambda item: (
                    item.total_uncertainty,
                    -item.total_utility,
                    item.total_tokens,
                ),
            )

        # Balanced ordering is applied only after Pareto filtering. Normalize each
        # dimension so no unit (tokens vs. tool calls) wins merely by scale.
        def ranges(attribute: str) -> tuple[float, float]:
            values = [float(getattr(item, attribute)) for item in frontier]
            return min(values), max(values)

        dimensions = {
            "total_utility": (True, ranges("total_utility")),
            "jobs_run": (True, ranges("jobs_run")),
            "total_tokens": (False, ranges("total_tokens")),
            "total_tool_calls": (False, ranges("total_tool_calls")),
            "total_parallel_agents": (False, ranges("total_parallel_agents")),
            "total_uncertainty": (False, ranges("total_uncertainty")),
        }

        def normalized(value: float, low: float, high: float) -> float:
            return 0.0 if high == low else (value - low) / (high - low)

        def score(item: ReasoningAllocation) -> tuple[float, float, int]:
            total = 0.0
            for attribute, (gain, (low, high)) in dimensions.items():
                value = normalized(float(getattr(item, attribute)), low, high)
                total += value if gain else -value
            return (total, item.total_utility, -item.total_tokens)

        return max(frontier, key=score)

    def materialize_ledger(
        self,
        allocation: ReasoningAllocation,
        *,
        entropy_freeze_threshold: float = 4.5,
        prefix: str = "portfolio:",
    ) -> ReasoningBudgetLedger:
        """Mint a fresh fail-closed ledger from a selected allocation atomically.

        A new ledger is built from scratch so a mint failure cannot partially mutate
        caller-owned state. The selected token/tool/agent ceilings become the exact
        execution envelopes consumed by the existing ledger implementation.
        """

        ledger = ReasoningBudgetLedger(entropy_freeze_threshold=entropy_freeze_threshold)
        for choice in allocation.choices:
            ledger.mint(
                f"{prefix}{choice.job_id}",
                choice.tier.tokens,
                max_parallel_agents=choice.tier.parallel_agents,
                max_tool_calls=choice.tier.tool_calls,
            )
        return ledger
