from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Material:
    name: str
    youngs_modulus_mpa: float
    yield_strength_mpa: float
    density_g_per_mm3: float
    thermal_expansion_per_c: float
    base_cost_jpy_per_kg: float
    machinable: bool
    min_wall_thickness_mm: float
    min_inner_radius_mm: float


MATERIALS: dict[str, Material] = {
    "aluminum_7075_t6": Material(
        name="aluminum_7075_t6",
        youngs_modulus_mpa=71_700.0,
        yield_strength_mpa=503.0,
        density_g_per_mm3=0.00281,
        thermal_expansion_per_c=23.5e-6,
        base_cost_jpy_per_kg=900.0,
        machinable=True,
        min_wall_thickness_mm=1.2,
        min_inner_radius_mm=0.8,
    ),
    "titanium_6al4v": Material(
        name="titanium_6al4v",
        youngs_modulus_mpa=113_800.0,
        yield_strength_mpa=880.0,
        density_g_per_mm3=0.00443,
        thermal_expansion_per_c=8.6e-6,
        base_cost_jpy_per_kg=7_000.0,
        machinable=True,
        min_wall_thickness_mm=0.9,
        min_inner_radius_mm=0.6,
    ),
    "cfrp_quasi_isotropic": Material(
        name="cfrp_quasi_isotropic",
        youngs_modulus_mpa=70_000.0,
        yield_strength_mpa=620.0,
        density_g_per_mm3=0.00160,
        thermal_expansion_per_c=2.0e-6,
        base_cost_jpy_per_kg=12_000.0,
        machinable=False,
        min_wall_thickness_mm=1.8,
        min_inner_radius_mm=1.5,
    ),
    "magnesium_az31": Material(
        name="magnesium_az31",
        youngs_modulus_mpa=45_000.0,
        yield_strength_mpa=200.0,
        density_g_per_mm3=0.00178,
        thermal_expansion_per_c=26.0e-6,
        base_cost_jpy_per_kg=1_400.0,
        machinable=True,
        min_wall_thickness_mm=1.5,
        min_inner_radius_mm=1.0,
    ),
}

