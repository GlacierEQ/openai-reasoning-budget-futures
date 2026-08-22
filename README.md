# Reasoning Budget Futures + Portfolio Exchange

Independent GlacierEQ engineering work on precommitted reasoning-resource envelopes and deterministic portfolio allocation for tool-using agent workloads.

**Core evidence state:** repository-local deterministic models and execution receipts.  
**Portfolio evidence token:** `DETERMINISTIC_REASONING_PORTFOLIO_MODEL`

This repository is not affiliated with, endorsed by, or operated by OpenAI. It does not claim OpenAI adoption, production scheduler deployment, proprietary access, measured model-quality improvement, or provider-accurate token/tool accounting.

## Central mechanism

`src/budget_futures.py` remains the fail-closed execution ledger. A `BudgetFuture` precommits ceilings for tokens, tool calls, and parallel agents; execution is refused before mutation when a request exceeds an envelope, and entropy spikes can freeze a future before spend.

The new `src/budget_exchange.py` composes that mechanism upward into a multi-job reasoning-futures exchange:

1. each job submits one or more explicit resource/utility/uncertainty tiers;
2. jobs may be mandatory or optional;
3. the exchange enumerates only portfolios that fit the declared token, tool-call, and parallel-agent pool;
4. a hard `max_combinations` ceiling refuses unsafe exponential search before enumeration;
5. mandatory work that cannot fit fails closed with `NoFeasibleAllocation`;
6. feasible allocations are Pareto-filtered before any preference ordering;
7. value, efficiency, risk, or normalized balanced preferences order only the non-dominated frontier;
8. the selected portfolio can be materialized into a fresh `ReasoningBudgetLedger`, preserving the original execution-enforcement semantics rather than replacing them.

The caller-declared `utility` and `uncertainty` values are planning inputs. They are **not** claims about measured model intelligence, correctness, or production performance.

## Executable portfolio proof

```bash
python scripts/portfolio_plan.py \
  --input machine/portfolio-demo.json \
  --preference value \
  --output .verification-artifacts/reasoning-portfolio.json
```

The output contains the complete non-dominated frontier and selected allocation. A companion receipt binds the exact artifact bytes to SHA-256 and labels the achieved state `DETERMINISTIC_PORTFOLIO_MODEL_EXECUTED`.

The checked-in demonstration has a 400-token / 4-tool / 3-agent pool. The value preference must select the required `train-a:deep` tier together with `eval-b:quick`, consuming the pool exactly while achieving declared utility 13. That scenario is asserted again in repository-owned CI rather than trusted from documentation.

## Engineering lineage actually adopted

| Source | Mechanism adopted | Local implementation |
|---|---|---|
| `GlacierEQ/pro-code` | failure paths are first-class, execution leaves receipts, complexity must buy capability | resource refusal, search-size refusal, hash-linked plan receipts |
| `GlacierEQ/Pro_Code` | doctrine becomes meaningful only through target-repository source/tests/verification | adoption is pinned in `machine/integration-lineage.json` and checked in CI |
| `GlacierEQ/glaciereq-excellence-core` | Pareto dominance precedes preference ordering | `ReasoningFuturesExchange.pareto_frontier()` preserves real resource/value/risk tradeoffs |
| `GlacierEQ/apex-control-plane` | generated, executed, verified, and promoted are distinct states | execution receipts are deliberately narrower than provider/runtime claims |
| `GlacierEQ/public-actions-runner-host` | reusable strict verification around a repository-owned proof script | `.github/workflows/elite-core.yml` executes `scripts/ci/verify_elite_core.sh` and uploads proof artifacts |

Exact source blob revisions and local evidence paths are recorded in `machine/integration-lineage.json`. These are code/verification adoptions, not claims of live cross-repository runtime connectivity.

## Proof surface

- `src/budget_futures.py` — existing token/tool/parallel execution-envelope ledger;
- `src/budget_exchange.py` — multi-job capacity planning, Pareto frontier, selection, and ledger materialization;
- `tests/test_budget_futures.py` — original envelope/refusal/freeze behavior;
- `tests/test_budget_exchange.py` — portfolio composition, non-domination, mandatory-work refusal, materialized-ledger enforcement, invalid inputs, and combinatorial-explosion refusal;
- `scripts/portfolio_plan.py` — executable JSON planner and SHA-256 receipt generator;
- `machine/portfolio-demo.json` — deterministic verification scenario;
- `scripts/ci/verify_elite_core.sh` — repository-owned integrated proof;
- `.github/workflows/elite-core.yml` — strict shared GlacierEQ verification runner.

Native verification:

```bash
python -m compileall -q src tests scripts
python -m unittest discover -s tests -v
bash scripts/ci/verify_elite_core.sh
```

## Preserved strengths

This expansion does not delete or dilute the original prepaid-future mechanism. It keeps:

- unique future IDs;
- remaining-budget metering;
- over-budget refusal before spend;
- nonpositive-spend refusal;
- cumulative tool-call ceilings;
- parallel-agent ceilings;
- entropy-triggered pre-spend freeze;
- frozen-budget refusal;
- deterministic spend fingerprints.

The exchange adds a planning layer above those controls and ultimately hands execution back to the original ledger.

## Explicit nonclaims

Current repository evidence does **not** establish:

- OpenAI affiliation, employment, endorsement, adoption, or proprietary access;
- integration with OpenAI internal schedulers or reasoning infrastructure;
- provider-accurate token or tool-call reconciliation;
- measured model-quality, latency, throughput, or cost improvement;
- autonomous production resource purchasing;
- exercised runtime integration with adjacent `openai-*` GlacierEQ repositories;
- utility or uncertainty values derived from a live model evaluator.

Those require separate provider/runtime/benchmark evidence.

## Why this is a stronger system

A token budget by itself answers, “may this one job spend?” The exchange answers the harder question, “given several competing jobs and multiple execution shapes, which combinations remain feasible and non-dominated, and can the selected plan be turned into enforceable envelopes without oversubscription?”

```text
BIDS
  -> FEASIBLE PORTFOLIOS
  -> PARETO FRONTIER
  -> DECLARED PREFERENCE
  -> SELECTED PORTFOLIO
  -> FAIL-CLOSED LEDGER ENVELOPES
  -> EXECUTION RECEIPTS
```

The result is still deterministic and inspectable, but it now exercises composition, refusal, optimization, provenance, and execution enforcement as one coherent mechanism.
