#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR=".verification-artifacts"
PLAN="${ARTIFACT_DIR}/reasoning-portfolio.json"
RECEIPT="${ARTIFACT_DIR}/reasoning-portfolio.receipt.json"
mkdir -p "${ARTIFACT_DIR}"

python -m compileall -q src tests scripts
python -m unittest discover -s tests -v | tee "${ARTIFACT_DIR}/unittest.txt"

python scripts/portfolio_plan.py \
  --input machine/portfolio-demo.json \
  --preference value \
  --output "${PLAN}" \
  --receipt "${RECEIPT}" \
  | tee "${ARTIFACT_DIR}/portfolio-plan.txt"

python - <<'PY'
import hashlib
import json
from pathlib import Path

plan_path = Path('.verification-artifacts/reasoning-portfolio.json')
receipt_path = Path('.verification-artifacts/reasoning-portfolio.receipt.json')
plan = json.loads(plan_path.read_text(encoding='utf-8'))
receipt = json.loads(receipt_path.read_text(encoding='utf-8'))

assert plan['schema'] == 'glaciereq.reasoning-futures-portfolio.v1'
assert plan['evidence_state'] == 'DETERMINISTIC_REASONING_PORTFOLIO_MODEL'
assert plan['combination_count'] == 6
assert plan['frontier_count'] >= 1
selected = plan['selected']
assert selected['total_utility'] == 13.0
assert selected['total_tokens'] == 400
assert selected['total_tool_calls'] == 4
assert selected['total_parallel_agents'] == 3
assert [(row['job_id'], row['tier']['name']) for row in selected['choices']] == [
    ('train-a', 'deep'),
    ('eval-b', 'quick'),
]
actual = hashlib.sha256(plan_path.read_bytes()).hexdigest()
assert receipt['artifact_sha256'] == actual
assert receipt['verified_state'] == 'DETERMINISTIC_PORTFOLIO_MODEL_EXECUTED'
print(json.dumps({
    'elite_core': 'PASS',
    'frontier_count': plan['frontier_count'],
    'selected': selected,
    'artifact_sha256': actual,
}, indent=2))
PY
