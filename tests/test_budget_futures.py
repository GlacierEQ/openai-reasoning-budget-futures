from __future__ import annotations
import unittest
from src.budget_futures import ReasoningBudgetLedger, SpendStatus


class BudgetTests(unittest.TestCase):
    def test_over_budget(self):
        led = ReasoningBudgetLedger()
        led.mint("f1", 100)
        r = led.spend("f1", 120)
        self.assertEqual(r.status, SpendStatus.REFUSED)

    def test_entropy_freeze(self):
        led = ReasoningBudgetLedger(entropy_freeze_threshold=3.0)
        led.mint("f1", 100)
        r = led.spend("f1", 10, entropy=4.0)
        self.assertEqual(r.status, SpendStatus.FROZEN)
        r2 = led.spend("f1", 1)
        self.assertEqual(r2.status, SpendStatus.FROZEN)

    def test_meter(self):
        led = ReasoningBudgetLedger()
        led.mint("f1", 50)
        r = led.spend("f1", 20)
        self.assertEqual(r.remaining, 30)

    def test_parallelism_limit_refuses_without_spend(self):
        led = ReasoningBudgetLedger()
        led.mint("f1", 1000, max_parallel_agents=4, max_tool_calls=20)
        r = led.authorize_execution("f1", 200, parallel_agents=5, tool_calls=2)
        self.assertEqual(r.status, SpendStatus.REFUSED)
        self.assertEqual(r.reason, "PARALLELISM_LIMIT")
        self.assertEqual(r.remaining, 1000)
        self.assertEqual(r.tool_calls_remaining, 20)

    def test_tool_call_budget_is_cumulative(self):
        led = ReasoningBudgetLedger()
        led.mint("f1", 1000, max_parallel_agents=8, max_tool_calls=5)
        ok = led.authorize_execution("f1", 100, parallel_agents=4, tool_calls=3)
        self.assertEqual(ok.status, SpendStatus.OK)
        self.assertEqual(ok.remaining, 900)
        self.assertEqual(ok.tool_calls_remaining, 2)

        refused = led.authorize_execution("f1", 100, parallel_agents=4, tool_calls=3)
        self.assertEqual(refused.status, SpendStatus.REFUSED)
        self.assertEqual(refused.reason, "TOOL_CALL_BUDGET")
        self.assertEqual(refused.remaining, 900)
        self.assertEqual(refused.tool_calls_remaining, 2)

    def test_legacy_spend_surface_preserves_unbounded_coordination_defaults(self):
        led = ReasoningBudgetLedger()
        f = led.mint("f1", 25)
        self.assertIsNone(f.max_parallel_agents)
        self.assertIsNone(f.max_tool_calls)
        r = led.spend("f1", 10)
        self.assertEqual(r.status, SpendStatus.OK)
        self.assertEqual(r.remaining, 15)

    def test_invalid_envelope_rejected_at_mint(self):
        led = ReasoningBudgetLedger()
        with self.assertRaises(ValueError):
            led.mint("bad-agents", 100, max_parallel_agents=0)
        with self.assertRaises(ValueError):
            led.mint("bad-tools", 100, max_tool_calls=-1)


if __name__ == "__main__":
    unittest.main()
