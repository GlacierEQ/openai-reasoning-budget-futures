"""Reasoning budget futures — prepaid envelopes with circuit-break."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum


def digest(obj: object) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class SpendStatus(str, Enum):
    OK = "OK"
    REFUSED = "REFUSED"
    FROZEN = "FROZEN"


@dataclass
class BudgetFuture:
    future_id: str
    max_tokens: int
    spent: int = 0
    frozen: bool = False
    freeze_reason: str | None = None

    def remaining(self) -> int:
        return max(0, self.max_tokens - self.spent)


@dataclass(frozen=True)
class SpendReceipt:
    status: SpendStatus
    spent_this: int
    remaining: int
    reason: str | None
    fingerprint: str


class ReasoningBudgetLedger:
    def __init__(self, entropy_freeze_threshold: float = 4.5):
        self._futures: dict[str, BudgetFuture] = {}
        self.entropy_freeze_threshold = entropy_freeze_threshold

    def mint(self, future_id: str, max_tokens: int) -> BudgetFuture:
        if max_tokens < 1:
            raise ValueError("max_tokens")
        if future_id in self._futures:
            raise ValueError("EXISTS")
        f = BudgetFuture(future_id, max_tokens)
        self._futures[future_id] = f
        return f

    def spend(self, future_id: str, tokens: int, entropy: float | None = None) -> SpendReceipt:
        f = self._futures[future_id]
        if f.frozen:
            body = {"s": "FROZEN", "r": f.freeze_reason}
            return SpendReceipt(SpendStatus.FROZEN, 0, f.remaining(), f.freeze_reason, digest(body))
        if tokens < 1:
            body = {"s": "REFUSED", "r": "BAD_SPEND"}
            return SpendReceipt(SpendStatus.REFUSED, 0, f.remaining(), "BAD_SPEND", digest(body))
        if tokens > f.remaining():
            body = {"s": "REFUSED", "r": "OVER_BUDGET"}
            return SpendReceipt(SpendStatus.REFUSED, 0, f.remaining(), "OVER_BUDGET", digest(body))
        if entropy is not None and entropy >= self.entropy_freeze_threshold:
            f.frozen = True
            f.freeze_reason = "ENTROPY_SPIKE"
            body = {"s": "FROZEN", "r": "ENTROPY_SPIKE", "e": entropy}
            return SpendReceipt(SpendStatus.FROZEN, 0, f.remaining(), "ENTROPY_SPIKE", digest(body))
        f.spent += tokens
        body = {"s": "OK", "spent": tokens, "rem": f.remaining()}
        return SpendReceipt(SpendStatus.OK, tokens, f.remaining(), None, digest(body))
