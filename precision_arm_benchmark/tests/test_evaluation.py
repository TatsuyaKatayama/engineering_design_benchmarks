import unittest

from armbench.evaluation import evaluate_reports, evaluate_single_report


def _strategy_report(planned_count=12):
    return {
        "extracted_information": [
            {"id": "static_tip_force", "value": 500.0, "source_ids": ["PF-002"]},
            {"id": "tip_torque", "value": 120.0, "source_ids": ["PF-023"]},
            {"id": "twist_angle_limit", "value": 0.01, "source_ids": ["PF-023"]},
            {"id": "aluminum_allowable_stress", "value": 170.0, "source_ids": ["PF-024"]},
            {
                "id": "first_bending_forbidden_band",
                "value": [80.0, 120.0],
                "source_ids": ["PF-001"],
            },
            {
                "id": "accelerance_target",
                "value": 9.149975745482665,
                "source_ids": ["generation_specs:gen3"],
            },
        ],
        "constraint_formulation": [
            {"id": "bending_stress", "criterion": "<=", "value": "material_allowable_stress"},
            {"id": "twist_angle", "criterion": "<=", "value": 0.01},
            {"id": "thermal_displacement", "criterion": "<=", "value": 0.15},
            {"id": "max_accelerance", "criterion": "<=", "value": 9.149975745482665},
            {"id": "first_bending_frequency", "criterion": "outside", "value": [80.0, 120.0]},
            {"id": "material_cost", "criterion": "minimize"},
        ],
        "planned_tools": [
            {"name": "search_failure_knowledge"},
            {"name": "get_generation_specs"},
            {"name": "calculate_section"},
            {"name": "calculate_bending"},
            {"name": "calculate_torsion"},
            {"name": "calculate_thermal_displacement"},
            {"name": "calculate_accelerance"},
            {"name": "calculate_cost"},
            {"name": "run_doe"},
        ],
        "exploration_plan": {
            "full_factorial_count": 12075,
            "planned_calculation_count": planned_count,
            "strategy": "limited DOE",
        },
        "candidate_comparison_plan": {"objective": "material_cost_minimization"},
    }


def _result_report(actual_count=12):
    return {
        "adopted_design": {
            "material": "aluminum_alloy",
            "length_mm": 450.0,
            "section": {
                "shape": "hollow_rect",
                "dimensions": {
                    "outer_height_mm": 30.0,
                    "outer_width_mm": 23.1,
                    "wall_thickness_mm": 1.7,
                },
            },
        },
        "constraint_results": [
            {"id": "bending_stress", "passed": True},
            {"id": "twist_angle", "passed": True},
            {"id": "thermal_displacement", "passed": True},
            {"id": "max_accelerance", "passed": True},
            {"id": "first_bending_frequency", "passed": True},
        ],
        "calculation_results": [{"candidate_id": "adopted", "outputs": {"cost_jpy": 184.78}}],
        "used_tools": [
            {"name": "search_failure_knowledge"},
            {"name": "get_generation_specs"},
            {"name": "calculate_section"},
            {"name": "calculate_bending"},
            {"name": "calculate_torsion"},
            {"name": "calculate_thermal_displacement"},
            {"name": "calculate_accelerance"},
            {"name": "calculate_cost"},
            {"name": "run_doe"},
        ],
        "actual_calculation_count": actual_count,
        "planned_vs_actual_summary": {"planned_calculation_count": actual_count},
        "minimum_cost_rationale": "cheapest feasible DOE row",
        "rejected_candidates": [{"candidate_id": "lower_cost_ng", "reason": "constraint failure"}],
        "adoption_rationale": "feasible and cheapest",
        "risk_responses": [{"risk_id": "PF-023", "response": "twist checked"}],
    }


class EvaluationTest(unittest.TestCase):
    def test_scores_best_known_solution(self):
        result = evaluate_reports(_strategy_report(), _result_report())

        self.assertEqual(result["scores"]["information_extraction"], 1.0)
        self.assertEqual(result["scores"]["constraint_formulation"], 1.0)
        self.assertEqual(result["scores"]["tool_selection"], 1.0)
        self.assertEqual(result["scores"]["optimization"], 1.0)
        self.assertEqual(result["details"]["optimization"]["rank"], 1)

    def test_report_score_fields_are_penalized(self):
        result_report = _result_report()
        result_report["optimization_score"] = 1.0

        result = evaluate_reports(_strategy_report(), result_report)

        self.assertLess(result["scores"]["report_requirements"], 1.0)
        self.assertIn("result.optimization_score", result["details"]["report_requirements"]["forbidden_score_fields"])

    def test_invalid_adopted_design_gets_negative_optimization(self):
        result_report = _result_report()
        result_report["adopted_design"]["section"]["dimensions"]["wall_thickness_mm"] = 1.2

        result = evaluate_reports(_strategy_report(), result_report)

        self.assertEqual(result["scores"]["optimization"], -1.0)

    def test_strategy_report_can_be_evaluated_alone(self):
        result = evaluate_single_report(_strategy_report())

        self.assertEqual(result["report_type"], "strategy")
        self.assertEqual(result["scores"]["information_extraction"], 1.0)
        self.assertEqual(result["scores"]["constraint_formulation"], 1.0)
        self.assertNotIn("optimization", result["scores"])

    def test_result_report_can_be_evaluated_alone(self):
        result = evaluate_single_report(_result_report())

        self.assertEqual(result["report_type"], "result")
        self.assertEqual(result["scores"]["optimization"], 1.0)
        self.assertEqual(result["details"]["optimization"]["rank"], 1)
        self.assertNotIn("information_extraction", result["scores"])


if __name__ == "__main__":
    unittest.main()
