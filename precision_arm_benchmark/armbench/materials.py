from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Material:
    name: str
    youngs_modulus_mpa: float
    poisson_ratio: float
    yield_strength_mpa: float
    density_g_per_mm3: float
    thermal_expansion_per_c: float
    cost_jpy_per_kg: float

    @property
    def shear_modulus_mpa(self) -> float:
        return self.youngs_modulus_mpa / (2.0 * (1.0 + self.poisson_ratio))


MATERIALS: dict[str, Material] = {
    "steel": Material(
        name="steel",
        youngs_modulus_mpa=200_000.0,
        poisson_ratio=0.30,
        yield_strength_mpa=160.0,
        density_g_per_mm3=0.00785,
        thermal_expansion_per_c=12.0e-6,
        cost_jpy_per_kg=360.0,
    ),
    "aluminum_alloy": Material(
        name="aluminum_alloy",
        youngs_modulus_mpa=70_000.0,
        poisson_ratio=0.33,
        yield_strength_mpa=250.0,
        density_g_per_mm3=0.00270,
        thermal_expansion_per_c=23.0e-6,
        cost_jpy_per_kg=900.0,
    ),
    "reinforced_plastic": Material(
        name="reinforced_plastic",
        youngs_modulus_mpa=25_000.0,
        poisson_ratio=0.35,
        yield_strength_mpa=180.0,
        density_g_per_mm3=0.00160,
        thermal_expansion_per_c=8.0e-6,
        cost_jpy_per_kg=1_500.0,
    ),
}
