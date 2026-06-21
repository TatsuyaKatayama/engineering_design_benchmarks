from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Section:
    shape: str
    dimensions: dict[str, float]

    def validate(self) -> None:
        if self.shape not in SECTION_SHAPES:
            raise ValueError(f"unknown section shape: {self.shape}")
        for name, value in self.dimensions.items():
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        calculate_section_properties(self)


@dataclass(frozen=True)
class SectionProperties:
    shape: str
    area_mm2: float
    second_moment_mm4: float
    section_modulus_mm3: float
    torsion_constant_mm4: float
    torsion_section_modulus_mm3: float

    def to_dict(self) -> dict[str, float | str]:
        return {
            "shape": self.shape,
            "area_mm2": self.area_mm2,
            "second_moment_mm4": self.second_moment_mm4,
            "section_modulus_mm3": self.section_modulus_mm3,
            "torsion_constant_mm4": self.torsion_constant_mm4,
            "torsion_section_modulus_mm3": self.torsion_section_modulus_mm3,
        }


SECTION_SHAPES = {
    "solid_round",
    "solid_rect",
    "hollow_round",
    "hollow_rect",
    "h_section",
}


def section_from_dict(data: dict[str, Any]) -> Section:
    shape = str(data["shape"])
    dimensions = {key: float(value) for key, value in data.get("dimensions", {}).items()}
    return Section(shape=shape, dimensions=dimensions)


def calculate_section_properties(section: Section) -> SectionProperties:
    match section.shape:
        case "solid_round":
            return solid_round_properties(section)
        case "solid_rect":
            return solid_rect_properties(section)
        case "hollow_round":
            return hollow_round_properties(section)
        case "hollow_rect":
            return hollow_rect_properties(section)
        case "h_section":
            return h_section_properties(section)
        case _:
            raise ValueError(f"unknown section shape: {section.shape}")


def solid_round_properties(section: Section) -> SectionProperties:
    d = require(section, "diameter_mm")
    area = math.pi * d**2 / 4.0
    second_moment = math.pi * d**4 / 64.0
    torsion_constant = math.pi * d**4 / 32.0
    return SectionProperties(
        shape=section.shape,
        area_mm2=area,
        second_moment_mm4=second_moment,
        section_modulus_mm3=second_moment / (d / 2.0),
        torsion_constant_mm4=torsion_constant,
        torsion_section_modulus_mm3=torsion_constant / (d / 2.0),
    )


def solid_rect_properties(section: Section) -> SectionProperties:
    width = require(section, "width_mm")
    height = require(section, "height_mm")
    area = width * height
    second_moment = width * height**3 / 12.0
    torsion_constant = rectangle_torsion_constant(width, height)
    return SectionProperties(
        shape=section.shape,
        area_mm2=area,
        second_moment_mm4=second_moment,
        section_modulus_mm3=second_moment / (height / 2.0),
        torsion_constant_mm4=torsion_constant,
        torsion_section_modulus_mm3=torsion_constant / (max(width, height) / 2.0),
    )


def hollow_round_properties(section: Section) -> SectionProperties:
    outer = require(section, "outer_diameter_mm")
    wall = require(section, "wall_thickness_mm")
    inner = outer - 2.0 * wall
    if inner <= 0:
        raise ValueError("wall_thickness_mm is too large for outer_diameter_mm")
    area = math.pi * (outer**2 - inner**2) / 4.0
    second_moment = math.pi * (outer**4 - inner**4) / 64.0
    torsion_constant = math.pi * (outer**4 - inner**4) / 32.0
    return SectionProperties(
        shape=section.shape,
        area_mm2=area,
        second_moment_mm4=second_moment,
        section_modulus_mm3=second_moment / (outer / 2.0),
        torsion_constant_mm4=torsion_constant,
        torsion_section_modulus_mm3=torsion_constant / (outer / 2.0),
    )


def hollow_rect_properties(section: Section) -> SectionProperties:
    width = require(section, "outer_width_mm")
    height = require(section, "outer_height_mm")
    wall = require(section, "wall_thickness_mm")
    inner_width = width - 2.0 * wall
    inner_height = height - 2.0 * wall
    if inner_width <= 0 or inner_height <= 0:
        raise ValueError("wall_thickness_mm is too large for outer dimensions")
    area = width * height - inner_width * inner_height
    second_moment = (width * height**3 - inner_width * inner_height**3) / 12.0
    midline_width = width - wall
    midline_height = height - wall
    enclosed_area = midline_width * midline_height
    torsion_constant = 4.0 * enclosed_area**2 / (2.0 * (midline_width + midline_height) / wall)
    return SectionProperties(
        shape=section.shape,
        area_mm2=area,
        second_moment_mm4=second_moment,
        section_modulus_mm3=second_moment / (height / 2.0),
        torsion_constant_mm4=torsion_constant,
        torsion_section_modulus_mm3=torsion_constant / (max(width, height) / 2.0),
    )


def h_section_properties(section: Section) -> SectionProperties:
    height = require(section, "height_mm")
    flange_width = require(section, "flange_width_mm")
    flange_thickness = require(section, "flange_thickness_mm")
    web_thickness = require(section, "web_thickness_mm")
    web_height = height - 2.0 * flange_thickness
    if web_height <= 0:
        raise ValueError("flange_thickness_mm is too large for height_mm")
    if web_thickness > flange_width:
        raise ValueError("web_thickness_mm must not exceed flange_width_mm")

    area = 2.0 * flange_width * flange_thickness + web_thickness * web_height
    y = height / 2.0 - flange_thickness / 2.0
    flange_i = flange_width * flange_thickness**3 / 12.0
    web_i = web_thickness * web_height**3 / 12.0
    second_moment = 2.0 * (flange_i + flange_width * flange_thickness * y**2) + web_i
    torsion_constant = (
        2.0 * flange_width * flange_thickness**3 + web_height * web_thickness**3
    ) / 3.0
    controlling_thickness = max(flange_thickness, web_thickness)
    return SectionProperties(
        shape=section.shape,
        area_mm2=area,
        second_moment_mm4=second_moment,
        section_modulus_mm3=second_moment / (height / 2.0),
        torsion_constant_mm4=torsion_constant,
        torsion_section_modulus_mm3=torsion_constant / controlling_thickness,
    )


def rectangle_torsion_constant(width: float, height: float) -> float:
    long_side = max(width, height)
    short_side = min(width, height)
    ratio = short_side / long_side
    return long_side * short_side**3 * (1.0 / 3.0 - 0.21 * ratio * (1.0 - ratio**4 / 12.0))


def require(section: Section, name: str) -> float:
    try:
        value = section.dimensions[name]
    except KeyError as exc:
        raise ValueError(f"{section.shape} requires {name}") from exc
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value

