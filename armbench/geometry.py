from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RectangularTube:
    length_mm: float
    outer_width_mm: float
    outer_height_mm: float
    wall_thickness_mm: float
    inner_radius_mm: float

    def validate(self) -> None:
        if self.length_mm <= 0:
            raise ValueError("length_mm must be positive")
        if self.outer_width_mm <= 0 or self.outer_height_mm <= 0:
            raise ValueError("outer dimensions must be positive")
        if self.wall_thickness_mm <= 0:
            raise ValueError("wall_thickness_mm must be positive")
        if self.inner_radius_mm < 0:
            raise ValueError("inner_radius_mm must be non-negative")
        if self.inner_width_mm <= 0 or self.inner_height_mm <= 0:
            raise ValueError("wall_thickness_mm is too large for the outer dimensions")

    @property
    def inner_width_mm(self) -> float:
        return self.outer_width_mm - 2.0 * self.wall_thickness_mm

    @property
    def inner_height_mm(self) -> float:
        return self.outer_height_mm - 2.0 * self.wall_thickness_mm

    @property
    def area_mm2(self) -> float:
        self.validate()
        return (
            self.outer_width_mm * self.outer_height_mm
            - self.inner_width_mm * self.inner_height_mm
        )

    @property
    def volume_mm3(self) -> float:
        return self.area_mm2 * self.length_mm

    @property
    def second_moment_mm4(self) -> float:
        self.validate()
        outer_i = self.outer_width_mm * self.outer_height_mm**3 / 12.0
        inner_i = self.inner_width_mm * self.inner_height_mm**3 / 12.0
        return outer_i - inner_i

    @property
    def section_modulus_mm3(self) -> float:
        return self.second_moment_mm4 / (self.outer_height_mm / 2.0)

