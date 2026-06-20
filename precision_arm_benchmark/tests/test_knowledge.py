import unittest

from armbench import get_generation_specs, search_failure_knowledge
from armbench.knowledge import load_past_failures


class KnowledgeTests(unittest.TestCase):
    def test_public_past_failures_load(self) -> None:
        records = load_past_failures()
        self.assertEqual(len(records), 20)
        self.assertEqual(records[0]["id"], "PF-001")

    def test_search_is_deterministic(self) -> None:
        first = search_failure_knowledge("50Hz sensor mass vibration", top_k=5)
        second = search_failure_knowledge("50Hz sensor mass vibration", top_k=5)
        self.assertEqual(first, second)

    def test_search_returns_vibration_failures_for_50hz_query(self) -> None:
        result = search_failure_knowledge("50Hz vibration transmissibility sensor mass", top_k=4)
        ids = [item["id"] for item in result["results"]]
        self.assertIn("PF-001", ids)
        self.assertIn("PF-003", ids)

    def test_search_returns_torsion_basis(self) -> None:
        result = search_failure_knowledge("H section open section torsion twist angle 120Nmm 0.01deg", top_k=5)
        ids = [item["id"] for item in result["results"]]
        self.assertIn("PF-023", ids)

    def test_search_returns_internal_standards(self) -> None:
        torsion = search_failure_knowledge("ねじり 社内基準 120Nmm 0.01deg", top_k=5)
        aluminum = search_failure_knowledge("アルミ 社内基準 170MPa 許容応力", top_k=5)
        self.assertIn("PF-023", [item["id"] for item in torsion["results"]])
        self.assertIn("PF-024", [item["id"] for item in aluminum["results"]])

    def test_search_returns_static_tip_force_basis(self) -> None:
        result = search_failure_knowledge("静的先端外乱荷重 500N 曲げ応力", top_k=5)
        self.assertIn("PF-002", [item["id"] for item in result["results"]])

    def test_generation_specs_can_fetch_gen2(self) -> None:
        result = get_generation_specs("gen2")
        specs = result["specs"]
        self.assertEqual(result["generation"], "gen2")
        self.assertEqual(specs["length_mm"], 550.0)
        self.assertEqual(specs["material"], "steel")
        self.assertEqual(specs["section"]["shape"], "hollow_rect")

    def test_generation_specs_can_fetch_gen3_reference(self) -> None:
        result = get_generation_specs("gen3")
        specs = result["specs"]
        self.assertEqual(result["generation"], "gen3")
        self.assertEqual(specs["material"], "aluminum_alloy")
        self.assertEqual(specs["section"]["shape"], "solid_rect")

    def test_unknown_generation_raises(self) -> None:
        with self.assertRaises(ValueError):
            get_generation_specs("gen9")


if __name__ == "__main__":
    unittest.main()
