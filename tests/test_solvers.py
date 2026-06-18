import unittest

from armbench import MATERIALS, DesignInput, RectangularTube
from armbench.solvers import (
    check_manufacturability,
    evaluate_design,
    solve_economics,
    solve_structural,
    solve_thermal,
    solve_vibration,
)


def baseline_design() -> DesignInput:
    return DesignInput(
        geometry=RectangularTube(
            length_mm=260.0,
            outer_width_mm=26.0,
            outer_height_mm=32.0,
            wall_thickness_mm=2.0,
            inner_radius_mm=1.0,
        ),
        material=MATERIALS["aluminum_7075_t6"],
        tip_mass_g=150.0,
        damping_ratio=0.03,
        temperature_delta_c=12.0,
        machining_cost_factor=2.2,
    )


class SolverTests(unittest.TestCase):
    def test_structural_returns_positive_metrics(self) -> None:
        result = solve_structural(baseline_design())
        self.assertGreater(result["tip_deflection_mm"], 0.0)
        self.assertGreater(result["max_bending_stress_mpa"], 0.0)
        self.assertGreater(result["safety_factor"], 1.0)

    def test_larger_height_reduces_deflection(self) -> None:
        base = baseline_design()
        taller = DesignInput(
            geometry=RectangularTube(
                length_mm=260.0,
                outer_width_mm=26.0,
                outer_height_mm=40.0,
                wall_thickness_mm=2.0,
                inner_radius_mm=1.0,
            ),
            material=base.material,
            tip_mass_g=base.tip_mass_g,
            damping_ratio=base.damping_ratio,
            temperature_delta_c=base.temperature_delta_c,
            machining_cost_factor=base.machining_cost_factor,
        )
        self.assertLess(
            solve_structural(taller)["tip_deflection_mm"],
            solve_structural(base)["tip_deflection_mm"],
        )

    def test_vibration_frequency_is_positive(self) -> None:
        result = solve_vibration(baseline_design())
        self.assertGreater(result["first_natural_frequency_hz"], 0.0)
        self.assertGreater(result["transmissibility_at_50hz"], 0.0)

    def test_economics_mass_matches_volume_density(self) -> None:
        design = baseline_design()
        result = solve_economics(design)
        expected_mass = design.geometry.volume_mm3 * design.material.density_g_per_mm3
        self.assertAlmostEqual(result["arm_mass_g"], expected_mass)

    def test_thermal_uses_material_alpha(self) -> None:
        result = solve_thermal(baseline_design())
        self.assertAlmostEqual(result["tip_thermal_displacement_mm"], 0.07332)

    def test_manufacturability_fails_for_thin_wall(self) -> None:
        base = baseline_design()
        thin = DesignInput(
            geometry=RectangularTube(
                length_mm=260.0,
                outer_width_mm=26.0,
                outer_height_mm=32.0,
                wall_thickness_mm=0.7,
                inner_radius_mm=1.0,
            ),
            material=base.material,
            tip_mass_g=base.tip_mass_g,
            damping_ratio=base.damping_ratio,
            temperature_delta_c=base.temperature_delta_c,
            machining_cost_factor=base.machining_cost_factor,
        )
        result = check_manufacturability(thin)
        self.assertFalse(result["pass"])
        self.assertTrue(result["reasons"])

    def test_evaluate_design_is_deterministic(self) -> None:
        first = evaluate_design(baseline_design())
        second = evaluate_design(baseline_design())
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()

