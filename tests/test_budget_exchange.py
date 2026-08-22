"""Deterministic and adversarial proof for the reasoning-futures exchange."""

import unittest

from src.budget_exchange import (
    EVIDENCE_STATE,
    NoFeasibleAllocation,
    PortfolioTooLarge,
    ReasoningBid,
    ReasoningFuturesExchange,
    ReasoningTier,
    ResourcePool,
)
from src.budget_futures import SpendStatus


class ReasoningFuturesExchangeTests(unittest.TestCase):
    def setUp(self):
        self.a = ReasoningBid(
            "train-a",
            (
                ReasoningTier("lean", 100, 1, 1, utility=4.0, uncertainty=1.0),
                ReasoningTier("deep", 300, 3, 2, utility=9.0, uncertainty=2.0),
            ),
            required=True,
        )
        self.b = ReasoningBid(
            "eval-b",
            (
                ReasoningTier("quick", 100, 1, 1, utility=4.0, uncertainty=0.5),
                ReasoningTier("deep", 250, 4, 2, utility=8.0, uncertainty=1.0),
            ),
        )
        self.exchange = ReasoningFuturesExchange(
            (self.a, self.b),
            ResourcePool(tokens=400, tool_calls=4, parallel_agents=3),
        )

    def test_value_selection_composes_jobs_without_oversubscription(self):
        selected = self.exchange.select("value")
        self.assertEqual(selected.total_utility, 13.0)
        self.assertEqual(selected.total_tokens, 400)
        self.assertEqual(selected.total_tool_calls, 4)
        self.assertEqual(selected.total_parallel_agents, 3)
        self.assertEqual(selected.jobs_run, 2)
        self.assertEqual(selected.evidence_state, EVIDENCE_STATE)
        self.assertEqual(
            [(choice.job_id, choice.tier.name) for choice in selected.choices],
            [("train-a", "deep"), ("eval-b", "quick")],
        )

    def test_frontier_contains_no_dominated_allocation(self):
        frontier = self.exchange.frontier()
        self.assertGreater(len(frontier), 1)
        for candidate in frontier:
            self.assertFalse(
                any(
                    other.dominates(candidate)
                    for other in frontier
                    if other is not candidate
                )
            )

    def test_materialized_ledger_enforces_selected_contracts(self):
        selected = self.exchange.select("value")
        ledger = self.exchange.materialize_ledger(selected)
        ok = ledger.authorize_execution(
            "portfolio:train-a",
            300,
            parallel_agents=2,
            tool_calls=3,
        )
        self.assertEqual(ok.status, SpendStatus.OK)
        refused = ledger.authorize_execution(
            "portfolio:eval-b",
            101,
            parallel_agents=1,
            tool_calls=1,
        )
        self.assertEqual(refused.status, SpendStatus.REFUSED)
        self.assertEqual(refused.reason, "OVER_BUDGET")

    def test_zero_tool_reasoning_job_remains_valid(self):
        bid = ReasoningBid(
            "reason-only",
            (ReasoningTier("local", 64, 0, 1, utility=2.0),),
            required=True,
        )
        exchange = ReasoningFuturesExchange(
            (bid,),
            ResourcePool(tokens=64, tool_calls=0, parallel_agents=1),
        )
        selected = exchange.select("value")
        self.assertEqual(selected.total_tool_calls, 0)
        ledger = exchange.materialize_ledger(selected)
        receipt = ledger.authorize_execution(
            "portfolio:reason-only",
            64,
            parallel_agents=1,
            tool_calls=0,
        )
        self.assertEqual(receipt.status, SpendStatus.OK)
        self.assertEqual(receipt.tool_calls_remaining, 0)

    def test_impossible_mandatory_work_refuses(self):
        exchange = ReasoningFuturesExchange(
            (self.a,),
            ResourcePool(tokens=50, tool_calls=1, parallel_agents=1),
        )
        with self.assertRaises(NoFeasibleAllocation):
            exchange.select()

    def test_combinatorial_explosion_fails_closed(self):
        tier_set = (
            ReasoningTier("a", 1, 1, 1, utility=1.0),
            ReasoningTier("b", 2, 1, 1, utility=2.0),
            ReasoningTier("c", 3, 1, 1, utility=3.0),
        )
        bids = tuple(ReasoningBid(f"job-{index}", tier_set) for index in range(5))
        exchange = ReasoningFuturesExchange(
            bids,
            ResourcePool(
                tokens=100,
                tool_calls=100,
                parallel_agents=100,
                max_combinations=100,
            ),
        )
        self.assertEqual(exchange.combination_count, 4**5)
        with self.assertRaises(PortfolioTooLarge):
            exchange.frontier()

    def test_invalid_inputs_fail_closed(self):
        with self.assertRaises(ValueError):
            ReasoningTier("", 1, 1, 1, utility=1.0)
        with self.assertRaises(ValueError):
            ReasoningTier("bad", 1, 1, 1, utility=float("nan"))
        with self.assertRaises(ValueError):
            ReasoningTier("bad-tools", 1, -1, 1, utility=1.0)
        with self.assertRaises(ValueError):
            ResourcePool(tokens=0, tool_calls=1, parallel_agents=1)
        with self.assertRaises(ValueError):
            ResourcePool(tokens=1, tool_calls=-1, parallel_agents=1)
        with self.assertRaises(ValueError):
            ReasoningFuturesExchange((self.a, self.a), ResourcePool(1000, 10, 10))
        with self.assertRaises(ValueError):
            self.exchange.select("magic")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
