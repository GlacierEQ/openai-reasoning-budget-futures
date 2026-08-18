import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = json.loads((ROOT / "machine" / "excellence-state.json").read_text(encoding="utf-8"))
POSITION = json.loads((ROOT / "machine" / "apex-position.json").read_text(encoding="utf-8"))
HISTORICAL_POSITION = json.loads((ROOT / "machine" / "apex-position.json").read_text(encoding="utf-8"))
CAPABILITIES = json.loads((ROOT / "machine" / "capabilities.json").read_text(encoding="utf-8"))


class ApexPositionContractTests(unittest.TestCase):
    def test_evolving_state_is_gate_complete(self):
        self.assertEqual(STATE["principal_state"], "EVOLVING")
        self.assertEqual(STATE["gates"]["APEX_POSITION_RESOLVED"]["status"], "PASS")
        self.assertEqual(STATE["gates"]["EVOLUTION_CURSOR_DEFINED"]["status"], "PASS")
        self.assertEqual(STATE["apex_position_ref"], "machine/apex-position.json")
        self.assertEqual(STATE["historical_position_ref"], "machine/apex-position.json")
        self.assertNotIn("APEX_POSITION_RESOLVED", STATE["gates"])

    def test_specialist_identity_lineage_and_human_authority_are_preserved(self):
        self.assertEqual(POSITION["source_identity"], "reasoning-budget-futures")
        policy = POSITION["integration_policy"]
        self.assertTrue(policy["preserve_repository_identity"])
        self.assertTrue(policy["preserve_lineage"])
        self.assertTrue(policy["absorption_requires_functional_equivalence"])
        self.assertTrue(policy["absorption_requires_proof_equivalence"])
        self.assertIn("Casey Barton", POSITION["authority_boundary"])
        self.assertIn("sole human authority", POSITION["authority_boundary"])

    def test_retired_position_artifact_is_historical_evidence_only(self):
        self.assertEqual(HISTORICAL_POSITION["canonical_identity"], "reasoning-budget-futures")
        historical = POSITION["historical_evidence"]
        self.assertEqual(historical["retired_position_artifact"], "machine/apex-position.json")
        self.assertIn("historical evidence only", historical["rule"])
        self.assertIn("no current authority", historical["rule"])

    def test_capabilities_name_repository_native_budget_mechanisms(self):
        self.assertEqual(CAPABILITIES["capability_family"], "precommitted_reasoning_budget_control")
        capabilities = set(CAPABILITIES["capabilities"])
        self.assertIn("remaining-budget-metering", capabilities)
        self.assertIn("over-budget-spend-refusal", capabilities)
        self.assertIn("entropy-spike-pre-spend-freeze", capabilities)
        self.assertIn("deterministic-spend-receipts", capabilities)
        self.assertNotIn("hyper-scaling", capabilities)

    def test_openai_edges_do_not_claim_integration(self):
        self.assertTrue(POSITION["relationships"])
        self.assertTrue(all(row["integration_state"] == "NOT_CLAIMED" for row in POSITION["relationships"]))

    def test_evolution_and_public_boundary_are_material(self):
        self.assertIn("hierarchical/attenuating", POSITION["next_evolution"])
        self.assertIn("no OpenAI affiliation", POSITION["nonclaims"])
        self.assertIn("No OpenAI adoption", CAPABILITIES["truth_boundary"])


if __name__ == "__main__":
    unittest.main()
