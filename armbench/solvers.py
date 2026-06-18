from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .geometry import RectangularTube
from .materials import MATERIALS, Material

GRAVITY_M_PER_S2 = 9.80665


@dataclass(frozen=True)
class DesignInput:
    geometry: RectangularTube
    material: Material
    tip_mass_g: float
    damping_ratio: float
    temperature_delta_c: float
    machining_cost_factor: float

    def validate(self) -> None:
        self.geometry.validate()
        if self.tip_mass_g < 0:
            raise ValueError("tip_mass_g must be non-negative")
        if self.damping_ratio <= 0:
            raise ValueError("damping_ratio must be positive")
        if self.machining_cost_factor < 0:
            raise ValueError("machining_cost_factor must be non-negative")


def design_from_dict(data: dict[str, Any]) -> DesignInput:
    material_name = str(data["material"])
    if material_name not in MATERIALS:
        raise ValueError(f"unknown material: {material_name}")
    geometry = RectangularTube(
        length_mm=float(data["length_mm"]),
        outer_width_mm=float(data["outer_width_mm"]),
        outer_height_mm=float(data["outer_height_mm"]),
        wall_thickness_mm=float(data["wall_thickness_mm"]),
        inner_radius_mm=float(data.get("inner_radius_mm", 0.0)),
    )
    return DesignInput(
        geometry=geometry,
        material=MATERIALS[material_name],
        tip_mass_g=float(data["tip_mass_g"]),
        damping_ratio=float(data.get("damping_ratio", 0.03)),
        temperature_delta_c=float(data.get("temperature_delta_c", 10.0)),
        machining_cost_factor=float(data.get("machining_cost_factor", 1.0)),
    )


def arm_mass_g(geometry: RectangularTube, material: Material) -> float:
    return geometry.volume_mm3 * material.density_g_per_mm3


def solve_structural(design: DesignInput) -> dict[str, float]:
    design.validate()
    geom = design.geometry
    material = design.material

    length_m = geom.length_mm / 1000.0
    elastic_modulus_pa = material.youngs_modulus_mpa * 1e6
    second_moment_m4 = geom.second_moment_mm4 * 1e-12
    section_modulus_m3 = geom.section_modulus_mm3 * 1e-9
    tip_force_n = design.tip_mass_g / 1000.0 * GRAVITY_M_PER_S2
    distributed_load_n_per_m = (
        arm_mass_g(geom, material) / 1000.0 * GRAVITY_M_PER_S2 / length_m
    )

    tip_deflection_m = (
        tip_force_n * length_m**3 / (3.0 * elastic_modulus_pa * second_moment_m4)
        + distributed_load_n_per_m
        * length_m**4
        / (8.0 * elastic_modulus_pa * second_moment_m4)
    )
    max_moment_nm = (
        tip_force_n * length_m + distributed_load_n_per_m * length_m**2 / 2.0
    )
    max_stress_pa = max_moment_nm / section_modulus_m3
    max_stress_mpa = max_stress_pa / 1e6

    return {
        "tip_deflection_mm": tip_deflection_m * 1000.0,
        "max_bending_stress_mpa": max_stress_mpa,
        "safety_factor": material.yield_strength_mpa / max_stress_mpa,
    }


def solve_vibration(design: DesignInput) -> dict[str, float]:
    design.validate()
    geom = design.geometry
    material = design.material

    length_m = geom.length_mm / 1000.0
    elastic_modulus_pa = material.youngs_modulus_mpa * 1e6
    second_moment_m4 = geom.second_moment_mm4 * 1e-12
    stiffness_n_per_m = 3.0 * elastic_modulus_pa * second_moment_m4 / length_m**3
    modal_mass_kg = design.tip_mass_g / 1000.0 + 0.236 * arm_mass_g(geom, material) / 1000.0
    natural_frequency_hz = math.sqrt(stiffness_n_per_m / modal_mass_kg) / (2.0 * math.pi)

    excitation_hz = 50.0
    ratio = excitation_hz / natural_frequency_hz
    zeta = design.damping_ratio
    transmissibility = math.sqrt(
        (1.0 + (2.0 * zeta * ratio) ** 2)
        / ((1.0 - ratio**2) ** 2 + (2.0 * zeta * ratio) ** 2)
    )

    return {
        "first_natural_frequency_hz": natural_frequency_hz,
        "transmissibility_at_50hz": transmissibility,
    }


def solve_economics(design: DesignInput) -> dict[str, float]:
    design.validate()
    mass_g = arm_mass_g(design.geometry, design.material)
    material_cost_jpy = mass_g / 1000.0 * design.material.base_cost_jpy_per_kg
    total_cost_jpy = material_cost_jpy * (1.0 + design.machining_cost_factor)
    return {
        "arm_mass_g": mass_g,
        "material_cost_jpy": material_cost_jpy,
        "estimated_total_cost_jpy": total_cost_jpy,
    }


def solve_thermal(design: DesignInput) -> dict[str, float]:
    design.validate()
    displacement_mm = (
        design.geometry.length_mm
        * design.material.thermal_expansion_per_c
        * design.temperature_delta_c
    )
    return {"tip_thermal_displacement_mm": displacement_mm}


def check_manufacturability(design: DesignInput) -> dict[str, Any]:
    design.validate()
    geom = design.geometry
    material = design.material
    reasons: list[str] = []

    if geom.wall_thickness_mm < material.min_wall_thickness_mm:
        reasons.append(
            f"wall_thickness_mm {geom.wall_thickness_mm:.3f} < material minimum "
            f"{material.min_wall_thickness_mm:.3f}"
        )
    if geom.inner_radius_mm < material.min_inner_radius_mm:
        reasons.append(
            f"inner_radius_mm {geom.inner_radius_mm:.3f} < material minimum "
            f"{material.min_inner_radius_mm:.3f}"
        )
    if not material.machinable:
        reasons.append(f"material {material.name} is not approved for machining")

    return {"pass": len(reasons) == 0, "reasons": reasons}


def evaluate_design(design: DesignInput) -> dict[str, Any]:
    return {
        "structural": solve_structural(design),
        "vibration": solve_vibration(design),
        "economics": solve_economics(design),
        "thermal": solve_thermal(design),
        "manufacturability": check_manufacturability(design),
    }

