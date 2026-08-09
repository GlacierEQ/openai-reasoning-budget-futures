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

if __name__ == "__main__":
    unittest.main()
