import unittest

from armbench import (
    MATERIALS,
    DesignInput,
    Section,
    calculate_accelerance,
    calculate_bending,
    calculate_cost,
    calculate_section,
    calculate_torsion,
    evaluate_design,
    run_doe,
)


def baseline_design(section: Section | None = None) -> DesignInput:
    return DesignInput(
        section=section
        or Section(
            shape="hollow_rect",
            dimensions={
                "outer_width_mm": 26.0,
                "outer_height_mm": 32.0,
                "wall_thickness_mm": 2.0,
            },
        ),
        length_mm=260.0,
        material=MATERIALS["aluminum_alloy"],
        static_tip_force_n=500.0,
        dynamic_tip_mass_g=150.0,
        tip_torque_nmm=120.0,
        damping_ratio=0.03,
        temperature_delta_c=12.0,
        frequency_min_hz=0.0,
        frequency_max_hz=100.0,
        frequency_step_hz=0.5,
    )


class SolverTests(unittest.TestCase):
    def test_section_properties_for_solid_round_are_positive(self) -> None:
        result = calculate_section(Section("solid_round", {"diameter_mm": 20.0}))
        self.assertGreater(result["area_mm2"], 0.0)
        self.assertGreater(result["second_moment_mm4"], 0.0)
        self.assertGreater(result["torsion_constant_mm4"], result["second_moment_mm4"])

    def test_larger_height_reduces_bending_deflection(self) -> None:
        base = baseline_design()
        taller = baseline_design(
            Section(
                shape="hollow_rect",
                dimensions={
                    "outer_width_mm": 26.0,
                    "outer_height_mm": 40.0,
                    "wall_thickness_mm": 2.0,
                },
            )
        )
        self.assertLess(
            calculate_bending(taller)["tip_bending_deflection_mm"],
            calculate_bending(base)["tip_bending_deflection_mm"],
        )

    def test_h_section_is_weaker_in_torsion_than_hollow_rect_for_similar_size(self) -> None:
        h_section = baseline_design(
            Section(
                shape="h_section",
                dimensions={
                    "height_mm": 32.0,
                    "flange_width_mm": 26.0,
                    "flange_thickness_mm": 2.0,
                    "web_thickness_mm": 2.0,
                },
            )
        )
        hollow_rect = baseline_design()
        self.assertGreater(
            calculate_torsion(h_section)["twist_angle_deg"],
            calculate_torsion(hollow_rect)["twist_angle_deg"],
        )

    def test_cost_uses_section_area_density_and_material_unit_cost(self) -> None:
        design = baseline_design()
        section = calculate_section(design.section)
        mass_g = section["area_mm2"] * design.length_mm * design.material.density_g_per_mm3
        expected_cost = mass_g / 1000.0 * design.material.cost_jpy_per_kg
        result = calculate_cost(design)
        self.assertAlmostEqual(result["material_cost_jpy"], expected_cost)
        self.assertAlmostEqual(result["arm_mass_g_for_reference"], mass_g)

    def test_accelerance_reports_peak_in_range(self) -> None:
        result = calculate_accelerance(baseline_design())
        self.assertGreaterEqual(result["peak_frequency_hz"], 0.0)
        self.assertLessEqual(result["peak_frequency_hz"], 100.0)
        self.assertGreater(result["max_tip_accelerance_m_per_s2_per_n"], 0.0)

    def test_evaluate_design_is_deterministic(self) -> None:
        first = evaluate_design(baseline_design())
        second = evaluate_design(baseline_design())
        self.assertEqual(first, second)

    def test_doe_generates_all_candidates_without_selecting_best(self) -> None:
        result = run_doe(
            {
                "levels": 3,
                "materials": ["aluminum_alloy"],
                "length_mm": [240.0, 260.0],
                "fixed": {
                    "static_tip_force_n": 500.0,
                    "dynamic_tip_mass_g": 150.0,
                    "tip_torque_nmm": 120.0,
                    "damping_ratio": 0.03,
                    "temperature_delta_c": 12.0,
                },
                "sections": [
                    {
                        "shape": "solid_round",
                        "variables": {"diameter_mm": [16.0, 20.0]},
                    }
                ],
            }
        )
        self.assertEqual(result["candidate_count"], 9)
        self.assertIn("candidates", result)
        self.assertNotIn("best_candidate", result)


if __name__ == "__main__":
    unittest.main()
