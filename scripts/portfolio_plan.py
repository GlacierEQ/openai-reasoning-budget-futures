#!/usr/bin/env python3
"""Plan a reasoning-futures portfolio from JSON and emit a hash-linked receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from src.budget_exchange import (
    ReasoningBid,
    ReasoningFuturesExchange,
    ReasoningTier,
    ResourcePool,
)


def parse() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument(
        "--preference",
        choices=("balanced", "value", "efficiency", "risk"),
        default="balanced",
    )
    return parser.parse_args()


def load_exchange(path: Path) -> ReasoningFuturesExchange:
    raw = json.loads(path.read_text(encoding="utf-8"))
    pool = ResourcePool(**raw["pool"])
    bids = []
    for bid in raw["bids"]:
        tiers = tuple(ReasoningTier(**tier) for tier in bid["tiers"])
        bids.append(
            ReasoningBid(
                job_id=bid["job_id"],
                tiers=tiers,
                required=bool(bid.get("required", False)),
            )
        )
    return ReasoningFuturesExchange(bids, pool)


def main() -> int:
    args = parse()
    exchange = load_exchange(args.input)
    frontier = exchange.frontier()
    selected = exchange.select(args.preference)
    payload = {
        "schema": "glaciereq.reasoning-futures-portfolio.v1",
        "evidence_state": selected.evidence_state,
        "input": str(args.input),
        "preference": args.preference,
        "combination_count": exchange.combination_count,
        "feasible_count": len(exchange.feasible_allocations()),
        "frontier_count": len(frontier),
        "selected": selected.to_dict(),
        "frontier": [allocation.to_dict() for allocation in frontier],
        "claims_not_established": [
            "provider token accounting",
            "model quality improvement",
            "latency improvement",
            "production scheduler integration",
            "OpenAI internal infrastructure behavior",
        ],
        "integration_lineage": {
            "execution_envelopes": "src/budget_futures.py",
            "pareto_selection": "GlacierEQ/glaciereq-excellence-core pattern",
            "proof_discipline": "GlacierEQ/pro-code + GlacierEQ/apex-control-plane",
        },
    }
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encoded)

    receipt_path = args.receipt or args.output.with_suffix(args.output.suffix + ".receipt.json")
    receipt = {
        "schema": "glaciereq.reasoning-futures-portfolio-receipt.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": os.environ.get(
            "GITHUB_REPOSITORY", "GlacierEQ/openai-reasoning-budget-futures"
        ),
        "commit": os.environ.get("GITHUB_SHA", "local"),
        "artifact": str(args.output),
        "artifact_bytes": len(encoded),
        "artifact_sha256": hashlib.sha256(encoded).hexdigest(),
        "selected": selected.to_dict(),
        "verified_state": "DETERMINISTIC_PORTFOLIO_MODEL_EXECUTED",
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
