"""Auto-generated tests for ML Inference Optimization & KV-Cache Management."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from openai_reasoning_budget_futures.core import KVCacheConfig, ReasoningBudget, QuantizationPlanner

def test_bytes_per_token():
    cfg = KVCacheConfig(num_layers=32, num_heads=32, head_dim=128, max_seq_len=4096)
    bpt = cfg.bytes_per_token
    assert bpt == 2 * 32 * 32 * 128 * 2

def test_cache_size_gb():
    cfg = KVCacheConfig(num_layers=32, num_heads=32, head_dim=128, max_seq_len=4096)
    assert cfg.max_cache_gb > 0

def test_tokens_fitting_budget():
    cfg = KVCacheConfig(num_layers=32, num_heads=32, head_dim=128, max_seq_len=8192)
    tokens = cfg.tokens_fitting_budget(1.0)
    assert 0 < tokens < cfg.max_seq_len * 2

def test_reasoning_budget_cost():
    rb = ReasoningBudget(
        max_reasoning_tokens=10000, max_output_tokens=4000,
        cost_per_input_token=0.000003, cost_per_output_token=0.000015
    )
    cost = rb.total_cost(input_tokens=2000)
    assert cost > 0
    assert cost == 2000 * 0.000003 + 10000 * 0.000015 + 4000 * 0.000015

def test_cost_ratio():
    rb = ReasoningBudget(10000, 4000, 0.000003, 0.000015)
    assert rb.cost_ratio(1000) == 10000 / 4000

def test_quantization_planner():
    cfg = KVCacheConfig(num_layers=80, num_heads=64, head_dim=128, max_seq_len=32768)
    dtype = QuantizationPlanner.plan(cfg, target_gb=8.0)
    assert dtype is not None

def test_compression_ratio():
    assert QuantizationPlanner.compression_ratio("fp16", "int8") == 2.0
    assert QuantizationPlanner.compression_ratio("fp32", "int4") == 8.0

