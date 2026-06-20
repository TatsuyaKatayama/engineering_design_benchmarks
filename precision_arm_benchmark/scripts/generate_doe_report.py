from __future__ import annotations

import csv
import itertools
import json
import math
import sys
from pathlib import Path
from functools import lru_cache


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from armbench import DesignInput, MATERIALS, Section, evaluate_design, get_generation_specs  # noqa: E402
from armbench.geometry import calculate_section_properties  # noqa: E402
from armbench.solvers import level_values  # noqa: E402

REPORT_DIR = ROOT / "reports"
CSV_PATH = REPORT_DIR / "doe_sorted_regulation.csv"
MD_PATH = REPORT_DIR / "doe_summary.md"

MATERIAL_ALLOWABLE_MPA = {
    "steel": 250.0,
    "aluminum_alloy": 170.0,
    "reinforced_plastic": 120.0,
}

FIXED = {
    "static_tip_force_n": 500.0,
    "dynamic_tip_mass_g": 150.0,
    "tip_torque_nmm": 120.0,
    "damping_ratio": 0.03,
    "temperature_delta_c": 12.0,
    "frequency_min_hz": 0.0,
    "frequency_max_hz": 50.0,
    "frequency_step_hz": 0.5,
}

SECTIONS = [
    ("solid_round", {"diameter_mm": [1.2, 30.0]}),
    ("solid_rect", {"width_mm": [1.2, 30.0], "height_mm": [1.2, 30.0]}),
    ("hollow_round", {"outer_diameter_mm": [2.4, 30.0], "wall_thickness_mm": [1.2, 2.2]}),
    (
        "hollow_rect",
        {"outer_width_mm": [2.4, 30.0], "outer_height_mm": [2.4, 30.0], "wall_thickness_mm": [1.2, 2.2]},
    ),
    (
        "h_section",
        {
            "height_mm": [3.6, 30.0],
            "flange_width_mm": [1.2, 30.0],
            "flange_thickness_mm": [1.2, 2.2],
            "web_thickness_mm": [1.2, 2.2],
        },
    ),
]


def main() -> None:
    REPORT_DIR.mkdir(exist_ok=True)
    rows = []
    invalid_count = 0
    for shape, variables in SECTIONS:
        names = list(variables.keys())
        variable_levels = [level_values(variables[name], 5) for name in names]
        for material_name, length_mm, values in itertools.product(
            MATERIAL_ALLOWABLE_MPA,
            level_values([450.0, 550.0], 5),
            itertools.product(*variable_levels),
        ):
            dimensions = dict(zip(names, values, strict=True))
            try:
                design = DesignInput(
                    section=Section(shape, dimensions),
                    length_mm=length_mm,
                    material=MATERIALS[material_name],
                    **FIXED,
                )
                result = evaluate_design(design)
                section_props = calculate_section_properties(design.section)
            except Exception as exc:
                invalid_count += 1
                rows.append(invalid_row(material_name, shape, length_mm, dimensions, exc))
                continue

            first_bending_hz = estimate_first_bending_frequency(design, section_props.area_mm2, section_props.second_moment_mm4)
            reasons = ng_reasons(result, material_name, first_bending_hz)
            rows.append(
                {
                    "status": "PASS" if not reasons else "NG",
                    "ng_reasons": "; ".join(reasons),
                    "rag_links": "; ".join(rag_links(reasons, shape)),
                    "cost_jpy": result["cost"]["material_cost_jpy"],
                    "material": material_name,
                    "shape": shape,
                    "length_mm": length_mm,
                    "dimensions": json.dumps(dimensions, sort_keys=True),
                    "bending_stress_mpa": result["bending"]["max_bending_stress_mpa"],
                    "allowable_stress_mpa": MATERIAL_ALLOWABLE_MPA[material_name],
                    "twist_angle_deg": result["torsion"]["twist_angle_deg"],
                    "thermal_displacement_mm": result["thermal"]["tip_thermal_displacement_mm"],
                    "max_accelerance": result["accelerance"]["max_tip_accelerance_m_per_s2_per_n"],
                    "accelerance_peak_hz": result["accelerance"]["peak_frequency_hz"],
                    "first_bending_hz": first_bending_hz,
                    "bending_deflection_mm": result["bending"]["tip_bending_deflection_mm"],
                    "shear_stress_mpa": result["torsion"]["max_shear_stress_mpa"],
                    "reference_mass_g": result["cost"]["arm_mass_g_for_reference"],
                }
            )

    rows.sort(key=lambda row: (float(row["cost_jpy"]), row["status"], row["material"], row["shape"]))
    write_csv(rows)
    write_summary(rows, invalid_count)


def invalid_row(material_name: str, shape: str, length_mm: float, dimensions: dict[str, float], exc: Exception) -> dict[str, object]:
    return {
        "status": "NG",
        "ng_reasons": f"invalid_geometry: {exc}",
        "rag_links": "PF-021: DOE境界または不正な幾何条件の確認",
        "cost_jpy": math.inf,
        "material": material_name,
        "shape": shape,
        "length_mm": length_mm,
        "dimensions": json.dumps(dimensions, sort_keys=True),
        "bending_stress_mpa": "",
        "allowable_stress_mpa": MATERIAL_ALLOWABLE_MPA[material_name],
        "twist_angle_deg": "",
        "thermal_displacement_mm": "",
        "max_accelerance": "",
        "accelerance_peak_hz": "",
        "first_bending_hz": "",
        "bending_deflection_mm": "",
        "shear_stress_mpa": "",
        "reference_mass_g": "",
    }


def estimate_first_bending_frequency(design: DesignInput, area_mm2: float, second_moment_mm4: float) -> float:
    arm_mass_g = area_mm2 * design.length_mm * design.material.density_g_per_mm3
    length_m = design.length_mm / 1000.0
    elastic_modulus_pa = design.material.youngs_modulus_mpa * 1e6
    second_moment_m4 = second_moment_mm4 * 1e-12
    stiffness_n_per_m = 3.0 * elastic_modulus_pa * second_moment_m4 / length_m**3
    modal_mass_kg = design.dynamic_tip_mass_g / 1000.0 + 0.236 * arm_mass_g / 1000.0
    return math.sqrt(stiffness_n_per_m / modal_mass_kg) / (2.0 * math.pi)


def ng_reasons(result: dict, material_name: str, first_bending_hz: float) -> list[str]:
    reasons = []
    stress = result["bending"]["max_bending_stress_mpa"]
    if stress > MATERIAL_ALLOWABLE_MPA[material_name]:
        reasons.append(f"曲げ応力NG {stress:.2f}>{MATERIAL_ALLOWABLE_MPA[material_name]:.2f}MPa")
    twist = result["torsion"]["twist_angle_deg"]
    if twist > 0.01:
        reasons.append(f"ねじれ角NG {twist:.5f}>0.01000deg")
    thermal = result["thermal"]["tip_thermal_displacement_mm"]
    if thermal > 0.15:
        reasons.append(f"熱変位NG {thermal:.5f}>0.15000mm")
    accelerance = result["accelerance"]["max_tip_accelerance_m_per_s2_per_n"]
    accelerance_limit = reference_accelerance_limit()
    if accelerance > accelerance_limit:
        reasons.append(f"アクセレランスNG {accelerance:.3f}>{accelerance_limit:.3f}")
    if 80.0 <= first_bending_hz <= 120.0:
        reasons.append(f"固有値禁止帯NG {first_bending_hz:.2f}Hz in 80-120Hz")
    return reasons


@lru_cache(maxsize=1)
def reference_accelerance_limit() -> float:
    reference = get_generation_specs("gen3")["specs"]
    design = DesignInput(
        section=Section(reference["section"]["shape"], reference["section"]["dimensions"]),
        length_mm=reference["length_mm"],
        material=MATERIALS[reference["material"]],
        **FIXED,
    )
    return evaluate_design(design)["accelerance"]["max_tip_accelerance_m_per_s2_per_n"]


def rag_links(reasons: list[str], shape: str) -> list[str]:
    links = []
    for reason in reasons:
        if "曲げ応力NG" in reason:
            links.append("PF-002: 先端外乱荷重による根元曲げ応力")
        if "ねじれ角NG" in reason:
            links.append("PF-023: H型/開断面を含むねじれ角基準")
        if "熱変位NG" in reason:
            links.append("PF-004: 熱変位と測定オフセット")
        if "アクセレランスNG" in reason or "固有値禁止帯NG" in reason:
            links.append("PF-001/PF-003: 長尺化と外乱周波数の振動リスク")
    if shape == "h_section":
        links.append("PF-023: H型開断面ねじりリスク")
    return sorted(set(links))


def write_csv(rows: list[dict[str, object]]) -> None:
    fields = [
        "status",
        "ng_reasons",
        "rag_links",
        "cost_jpy",
        "material",
        "shape",
        "length_mm",
        "dimensions",
        "bending_stress_mpa",
        "allowable_stress_mpa",
        "twist_angle_deg",
        "thermal_displacement_mm",
        "max_accelerance",
        "accelerance_peak_hz",
        "first_bending_hz",
        "bending_deflection_mm",
        "shear_stress_mpa",
        "reference_mass_g",
    ]
    with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(rows: list[dict[str, object]], invalid_count: int) -> None:
    pass_rows = [row for row in rows if row["status"] == "PASS"]
    ng_rows = [row for row in rows if row["status"] == "NG" and row["cost_jpy"] != math.inf]
    lines = [
        "# DOE Regulation Summary",
        "",
        f"- total_rows: {len(rows)}",
        f"- pass_rows: {len(pass_rows)}",
        f"- ng_rows: {len(ng_rows)}",
        f"- invalid_geometry_rows: {invalid_count}",
        f"- accelerance_reference_limit: {reference_accelerance_limit():.6f} m/s^2/N",
        "",
        "## Cheapest PASS",
        "",
        table(pass_rows[:20]),
        "",
        "## Cheapest NG",
        "",
        table(ng_rows[:20]),
        "",
        "## RAG Coverage Note",
        "",
        "- 曲げ応力NGはPF-002で説明可能。",
        "- 熱変位NGはPF-004で説明可能。",
        "- アクセレランスNG/固有値禁止帯NGはPF-001/PF-003で説明可能。",
        "- DOE境界や不正幾何はPF-021で説明可能。",
        "- H型の開断面ねじりリスクと基準値はPF-023で説明可能。",
    ]
    MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def table(rows: list[dict[str, object]]) -> str:
    header = "| status | cost | material | shape | L | dimensions | stress | twist | thermal | acc | f1 | NG/RAG |"
    sep = "|---|---:|---|---|---:|---|---:|---:|---:|---:|---:|---|"
    body = []
    for row in rows:
        body.append(
            "| {status} | {cost:.2f} | {material} | {shape} | {length:.1f} | `{dims}` | {stress:.1f} | {twist:.4f} | {thermal:.3f} | {acc:.2f} | {f1:.1f} | {reason} {rag} |".format(
                status=row["status"],
                cost=float(row["cost_jpy"]),
                material=row["material"],
                shape=row["shape"],
                length=float(row["length_mm"]),
                dims=row["dimensions"],
                stress=float(row["bending_stress_mpa"]),
                twist=float(row["twist_angle_deg"]),
                thermal=float(row["thermal_displacement_mm"]),
                acc=float(row["max_accelerance"]),
                f1=float(row["first_bending_hz"]),
                reason=row["ng_reasons"],
                rag=row["rag_links"],
            )
        )
    return "\n".join([header, sep, *body])


if __name__ == "__main__":
    main()
