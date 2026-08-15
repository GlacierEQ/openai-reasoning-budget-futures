"""Reasoning budget futures — prepaid envelopes with fail-closed execution controls."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
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
    max_parallel_agents: int | None = None
    max_tool_calls: int | None = None
    spent: int = 0
    tool_calls_spent: int = 0
    frozen: bool = False
    freeze_reason: str | None = None

    def remaining(self) -> int:
        return max(0, self.max_tokens - self.spent)

    def remaining_tool_calls(self) -> int | None:
        if self.max_tool_calls is None:
            return None
        return max(0, self.max_tool_calls - self.tool_calls_spent)


@dataclass(frozen=True)
class SpendReceipt:
    status: SpendStatus
    spent_this: int
    remaining: int
    reason: str | None
    fingerprint: str
    parallel_agents: int = 1
    tool_calls_this: int = 0
    tool_calls_remaining: int | None = None


class ReasoningBudgetLedger:
    """Fail-closed ledger for token, tool-call, and parallel-agent execution envelopes.

    The original token-only ``mint``/``spend`` surface remains valid. New callers can
    precommit independent coordination limits and use ``authorize_execution`` for
    multi-agent/tool-heavy work without assuming any provider-specific implementation.
    """

    def __init__(self, entropy_freeze_threshold: float = 4.5):
        self._futures: dict[str, BudgetFuture] = {}
        self.entropy_freeze_threshold = entropy_freeze_threshold

    def mint(
        self,
        future_id: str,
        max_tokens: int,
        *,
        max_parallel_agents: int | None = None,
        max_tool_calls: int | None = None,
    ) -> BudgetFuture:
        if max_tokens < 1:
            raise ValueError("max_tokens")
        if max_parallel_agents is not None and max_parallel_agents < 1:
            raise ValueError("max_parallel_agents")
        if max_tool_calls is not None and max_tool_calls < 0:
            raise ValueError("max_tool_calls")
        if future_id in self._futures:
            raise ValueError("EXISTS")
        f = BudgetFuture(
            future_id=future_id,
            max_tokens=max_tokens,
            max_parallel_agents=max_parallel_agents,
            max_tool_calls=max_tool_calls,
        )
        self._futures[future_id] = f
        return f

    def _receipt(
        self,
        f: BudgetFuture,
        status: SpendStatus,
        *,
        spent_this: int = 0,
        reason: str | None = None,
        parallel_agents: int = 1,
        tool_calls_this: int = 0,
        entropy: float | None = None,
    ) -> SpendReceipt:
        body = {
            "s": status.value,
            "spent": spent_this,
            "rem": f.remaining(),
            "reason": reason,
            "parallel_agents": parallel_agents,
            "tool_calls": tool_calls_this,
            "tool_calls_remaining": f.remaining_tool_calls(),
        }
        if entropy is not None:
            body["entropy"] = entropy
        return SpendReceipt(
            status=status,
            spent_this=spent_this,
            remaining=f.remaining(),
            reason=reason,
            fingerprint=digest(body),
            parallel_agents=parallel_agents,
            tool_calls_this=tool_calls_this,
            tool_calls_remaining=f.remaining_tool_calls(),
        )

    def authorize_execution(
        self,
        future_id: str,
        tokens: int,
        *,
        parallel_agents: int = 1,
        tool_calls: int = 0,
        entropy: float | None = None,
    ) -> SpendReceipt:
        f = self._futures[future_id]
        if f.frozen:
            return self._receipt(
                f,
                SpendStatus.FROZEN,
                reason=f.freeze_reason,
                parallel_agents=parallel_agents,
                tool_calls_this=tool_calls,
            )
        if tokens < 1:
            return self._receipt(
                f,
                SpendStatus.REFUSED,
                reason="BAD_SPEND",
                parallel_agents=parallel_agents,
                tool_calls_this=tool_calls,
            )
        if parallel_agents < 1:
            return self._receipt(
                f,
                SpendStatus.REFUSED,
                reason="BAD_PARALLELISM",
                parallel_agents=parallel_agents,
                tool_calls_this=tool_calls,
            )
        if tool_calls < 0:
            return self._receipt(
                f,
                SpendStatus.REFUSED,
                reason="BAD_TOOL_CALLS",
                parallel_agents=parallel_agents,
                tool_calls_this=tool_calls,
            )
        if tokens > f.remaining():
            return self._receipt(
                f,
                SpendStatus.REFUSED,
                reason="OVER_BUDGET",
                parallel_agents=parallel_agents,
                tool_calls_this=tool_calls,
            )
        if f.max_parallel_agents is not None and parallel_agents > f.max_parallel_agents:
            return self._receipt(
                f,
                SpendStatus.REFUSED,
                reason="PARALLELISM_LIMIT",
                parallel_agents=parallel_agents,
                tool_calls_this=tool_calls,
            )
        remaining_tools = f.remaining_tool_calls()
        if remaining_tools is not None and tool_calls > remaining_tools:
            return self._receipt(
                f,
                SpendStatus.REFUSED,
                reason="TOOL_CALL_BUDGET",
                parallel_agents=parallel_agents,
                tool_calls_this=tool_calls,
            )
        if entropy is not None and entropy >= self.entropy_freeze_threshold:
            f.frozen = True
            f.freeze_reason = "ENTROPY_SPIKE"
            return self._receipt(
                f,
                SpendStatus.FROZEN,
                reason="ENTROPY_SPIKE",
                parallel_agents=parallel_agents,
                tool_calls_this=tool_calls,
                entropy=entropy,
            )

        f.spent += tokens
        f.tool_calls_spent += tool_calls
        return self._receipt(
            f,
            SpendStatus.OK,
            spent_this=tokens,
            parallel_agents=parallel_agents,
            tool_calls_this=tool_calls,
        )

    def spend(self, future_id: str, tokens: int, entropy: float | None = None) -> SpendReceipt:
        """Backward-compatible token-only spend path."""
        return self.authorize_execution(future_id, tokens, entropy=entropy)
