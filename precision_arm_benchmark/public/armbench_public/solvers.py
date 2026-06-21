from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Any

from .geometry import Section, SectionProperties, calculate_section_properties, section_from_dict
from .materials import MATERIALS, Material

GRAVITY_M_PER_S2 = 9.80665


@dataclass(frozen=True)
class DesignInput:
    section: Section
    length_mm: float
    material: Material
    static_tip_force_n: float
    dynamic_tip_mass_g: float
    tip_torque_nmm: float
    damping_ratio: float
    temperature_delta_c: float
    frequency_min_hz: float
    frequency_max_hz: float
    frequency_step_hz: float

    def validate(self) -> None:
        self.section.validate()
        if self.length_mm <= 0:
            raise ValueError("length_mm must be positive")
        if self.static_tip_force_n < 0:
            raise ValueError("static_tip_force_n must be non-negative")
        if self.dynamic_tip_mass_g < 0:
            raise ValueError("dynamic_tip_mass_g must be non-negative")
        if self.tip_torque_nmm < 0:
            raise ValueError("tip_torque_nmm must be non-negative")
        if self.damping_ratio <= 0:
            raise ValueError("damping_ratio must be positive")
        if self.frequency_min_hz < 0:
            raise ValueError("frequency_min_hz must be non-negative")
        if self.frequency_max_hz <= self.frequency_min_hz:
            raise ValueError("frequency_max_hz must be greater than frequency_min_hz")
        if self.frequency_step_hz <= 0:
            raise ValueError("frequency_step_hz must be positive")


def design_from_dict(data: dict[str, Any]) -> DesignInput:
    material_name = str(data["material"])
    if material_name not in MATERIALS:
        raise ValueError(f"unknown material: {material_name}")
    return DesignInput(
        section=section_from_dict(data["section"]),
        length_mm=float(data["length_mm"]),
        material=MATERIALS[material_name],
        static_tip_force_n=float(data["static_tip_force_n"]),
        dynamic_tip_mass_g=float(data["dynamic_tip_mass_g"]),
        tip_torque_nmm=float(data.get("tip_torque_nmm", 0.0)),
        damping_ratio=float(data.get("damping_ratio", 0.03)),
        temperature_delta_c=float(data.get("temperature_delta_c", 10.0)),
        frequency_min_hz=float(data.get("frequency_min_hz", 0.0)),
        frequency_max_hz=float(data.get("frequency_max_hz", 100.0)),
        frequency_step_hz=float(data.get("frequency_step_hz", 0.5)),
    )


def calculate_section(section: Section) -> dict[str, float | str]:
    return calculate_section_properties(section).to_dict()


def calculate_bending(design: DesignInput) -> dict[str, float]:
    design.validate()
    props = calculate_section_properties(design.section)
    arm_mass = calculate_arm_mass_g(design, props)

    length_m = design.length_mm / 1000.0
    elastic_modulus_pa = design.material.youngs_modulus_mpa * 1e6
    second_moment_m4 = props.second_moment_mm4 * 1e-12
    section_modulus_m3 = props.section_modulus_mm3 * 1e-9
    tip_force_n = design.static_tip_force_n
    distributed_load_n_per_m = arm_mass / 1000.0 * GRAVITY_M_PER_S2 / length_m

    tip_deflection_m = (
        tip_force_n * length_m**3 / (3.0 * elastic_modulus_pa * second_moment_m4)
        + distributed_load_n_per_m * length_m**4 / (8.0 * elastic_modulus_pa * second_moment_m4)
    )
    max_moment_nm = tip_force_n * length_m + distributed_load_n_per_m * length_m**2 / 2.0
    max_stress_mpa = (max_moment_nm / section_modulus_m3) / 1e6
    return {
        "tip_bending_deflection_mm": tip_deflection_m * 1000.0,
        "max_bending_stress_mpa": max_stress_mpa,
    }


def calculate_torsion(design: DesignInput) -> dict[str, float]:
    design.validate()
    props = calculate_section_properties(design.section)
    twist_rad = (
        design.tip_torque_nmm
        * design.length_mm
        / (design.material.shear_modulus_mpa * props.torsion_constant_mm4)
    )
    max_shear_stress_mpa = design.tip_torque_nmm / props.torsion_section_modulus_mm3
    return {
        "twist_angle_rad": twist_rad,
        "twist_angle_deg": math.degrees(twist_rad),
        "max_shear_stress_mpa": max_shear_stress_mpa,
    }


def calculate_cost(
    design: DesignInput,
    props: SectionProperties | None = None,
) -> dict[str, float]:
    design.validate()
    arm_mass_g = calculate_arm_mass_g(design, props)
    return {
        "material_cost_jpy": arm_mass_g / 1000.0 * design.material.cost_jpy_per_kg,
        "arm_mass_g_for_reference": arm_mass_g,
    }


def calculate_thermal_displacement(design: DesignInput) -> dict[str, float]:
    design.validate()
    displacement_mm = (
        design.length_mm
        * design.material.thermal_expansion_per_c
        * design.temperature_delta_c
    )
    return {"tip_thermal_displacement_mm": displacement_mm}


def calculate_accelerance(design: DesignInput) -> dict[str, float]:
    design.validate()
    props = calculate_section_properties(design.section)
    arm_mass_g = calculate_arm_mass_g(design, props)

    length_m = design.length_mm / 1000.0
    elastic_modulus_pa = design.material.youngs_modulus_mpa * 1e6
    second_moment_m4 = props.second_moment_mm4 * 1e-12
    stiffness_n_per_m = 3.0 * elastic_modulus_pa * second_moment_m4 / length_m**3
    modal_mass_kg = design.dynamic_tip_mass_g / 1000.0 + 0.236 * arm_mass_g / 1000.0
    damping_n_s_per_m = 2.0 * design.damping_ratio * math.sqrt(stiffness_n_per_m * modal_mass_kg)
    first_bending_frequency_hz = math.sqrt(stiffness_n_per_m / modal_mass_kg) / (2.0 * math.pi)
    peak_frequency_hz = design.frequency_min_hz
    max_accelerance = 0.0
    frequency = design.frequency_min_hz
    while frequency <= design.frequency_max_hz + 1e-12:
        omega = 2.0 * math.pi * frequency
        dynamic_stiffness_real = stiffness_n_per_m - modal_mass_kg * omega**2
        dynamic_stiffness_imag = damping_n_s_per_m * omega
        displacement_per_force = 1.0 / math.hypot(dynamic_stiffness_real, dynamic_stiffness_imag)
        accelerance = omega**2 * displacement_per_force
        if accelerance > max_accelerance:
            max_accelerance = accelerance
            peak_frequency_hz = frequency
        frequency += design.frequency_step_hz

    return {
        "max_tip_accelerance_m_per_s2_per_n": max_accelerance,
        "peak_frequency_hz": peak_frequency_hz,
        "first_bending_frequency_hz": first_bending_frequency_hz,
    }


def evaluate_design(design: DesignInput) -> dict[str, Any]:
    props = calculate_section_properties(design.section)
    return {
        "section": props.to_dict(),
        "bending": calculate_bending(design),
        "torsion": calculate_torsion(design),
        "cost": calculate_cost(design, props),
        "thermal": calculate_thermal_displacement(design),
        "accelerance": calculate_accelerance(design),
    }


def calculate_arm_mass_g(
    design: DesignInput,
    props: SectionProperties | None = None,
) -> float:
    section_props = props or calculate_section_properties(design.section)
    volume_mm3 = section_props.area_mm2 * design.length_mm
    return volume_mm3 * design.material.density_g_per_mm3


def run_doe(data: dict[str, Any]) -> dict[str, Any]:
    levels = int(data.get("levels", 5))
    if levels <= 1:
        raise ValueError("levels must be greater than 1")
    fixed = dict(data.get("fixed", {}))
    materials = [str(name) for name in data["materials"]]
    length_values = level_values(data["length_mm"], levels)

    results: list[dict[str, Any]] = []
    for section_plan in data["sections"]:
        shape = str(section_plan["shape"])
        variable_ranges = section_plan["variables"]
        variable_names = list(variable_ranges.keys())
        variable_levels = [level_values(variable_ranges[name], levels) for name in variable_names]
        for material, length_mm, values in itertools.product(materials, length_values, itertools.product(*variable_levels)):
            dimensions = dict(zip(variable_names, values, strict=True))
            design_data = {
                **fixed,
                "material": material,
                "length_mm": length_mm,
                "section": {"shape": shape, "dimensions": dimensions},
            }
            design = design_from_dict(design_data)
            results.append(
                {
                    "design": {
                        "section": {"shape": shape, "dimensions": dimensions},
                        "length_mm": length_mm,
                        "material": material,
                    },
                    "results": evaluate_design(design),
                }
            )

    return {
        "levels": levels,
        "candidate_count": len(results),
        "candidates": results,
    }


def level_values(bounds: Any, levels: int) -> list[float]:
    if not isinstance(bounds, list) or len(bounds) != 2:
        raise ValueError("DOE ranges must be [min, max]")
    lower = float(bounds[0])
    upper = float(bounds[1])
    if upper < lower:
        raise ValueError("DOE range max must be >= min")
    if levels == 1:
        return [lower]
    step = (upper - lower) / (levels - 1)
    return [lower + i * step for i in range(levels)]
