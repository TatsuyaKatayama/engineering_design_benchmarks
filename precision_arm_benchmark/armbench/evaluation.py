from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DOE_CSV = PROJECT_ROOT / "reports" / "doe_sorted_regulation.csv"

EXPECTED_ACCELERANCE_LIMIT = 9.149975745482665

REQUIRED_EXTRACTIONS = {
    "static_tip_force": {
        "aliases": {"static_tip_force", "static_tip_force_n"},
        "value": 500.0,
        "sources": {"PF-002"},
    },
    "tip_torque": {
        "aliases": {"tip_torque", "tip_torque_nmm", "tip_torsion_moment"},
        "value": 120.0,
        "sources": {"PF-023"},
    },
    "twist_angle_limit": {
        "aliases": {"twist_angle_limit", "twist_limit", "torsion_angle_limit"},
        "value": 0.01,
        "sources": {"PF-023"},
    },
    "aluminum_allowable_stress": {
        "aliases": {"aluminum_allowable_stress", "aluminum_allowable_stress_mpa"},
        "value": 170.0,
        "sources": {"PF-024"},
    },
    "first_bending_forbidden_band": {
        "aliases": {"first_bending_forbidden_band", "forbidden_frequency_band"},
        "value": [80.0, 120.0],
        "sources": {"PF-001", "PF-003"},
    },
    "accelerance_target": {
        "aliases": {"accelerance_target", "max_accelerance_limit", "accelerance_reference"},
        "value": EXPECTED_ACCELERANCE_LIMIT,
        "sources": {"gen3", "generation_specs:gen3", "public_generation_specs:gen3"},
    },
}

REQUIRED_CONSTRAINTS = {
    "bending_stress": {
        "aliases": {"bending_stress", "max_bending_stress"},
        "criterion": {"<=", "le", "less_equal"},
    },
    "twist_angle": {
        "aliases": {"twist_angle", "torsion_angle"},
        "criterion": {"<=", "le", "less_equal"},
        "value": 0.01,
    },
    "thermal_displacement": {
        "aliases": {"thermal_displacement", "tip_thermal_displacement"},
        "criterion": {"<=", "le", "less_equal"},
        "value": 0.15,
    },
    "max_accelerance": {
        "aliases": {"max_accelerance", "accelerance"},
        "criterion": {"<=", "le", "less_equal"},
        "value": EXPECTED_ACCELERANCE_LIMIT,
    },
    "first_bending_frequency": {
        "aliases": {"first_bending_frequency", "first_bending_hz"},
        "criterion": {"outside", "not_in", "exclude_range"},
        "value": [80.0, 120.0],
    },
    "material_cost": {
        "aliases": {"material_cost", "cost", "cost_jpy"},
        "criterion": {"minimize", "min", "minimum"},
    },
}

REQUIRED_TOOLS = {
    "search_failure_knowledge",
    "get_generation_specs",
    "calculate_section",
    "calculate_bending",
    "calculate_torsion",
    "calculate_thermal_displacement",
    "calculate_accelerance",
    "calculate_cost",
    "run_doe",
}

STRATEGY_REPORT_PATHS = [
    "extracted_information",
    "constraint_formulation",
    "planned_tools",
    "exploration_plan.full_factorial_count",
    "exploration_plan.planned_calculation_count",
    "exploration_plan.strategy",
    "candidate_comparison_plan",
]

RESULT_REPORT_PATHS = [
    "adopted_design",
    "constraint_results",
    "calculation_results",
    "used_tools",
    "actual_calculation_count",
    "planned_vs_actual_summary",
    "minimum_cost_rationale",
    "rejected_candidates",
    "adoption_rationale",
    "risk_responses",
]

DR_EXPLANATION_PATHS = [
    "adoption_rationale",
    "minimum_cost_rationale",
    "rejected_candidates",
    "constraint_results",
    "risk_responses",
]


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def evaluate_report_files(
    strategy_report_path: str | Path,
    result_report_path: str | Path,
    doe_csv_path: str | Path = DEFAULT_DOE_CSV,
) -> dict[str, Any]:
    strategy_report = load_json(strategy_report_path)
    result_report = load_json(result_report_path)
    return evaluate_reports(strategy_report, result_report, doe_csv_path)


def evaluate_single_report_file(
    report_path: str | Path,
    doe_csv_path: str | Path = DEFAULT_DOE_CSV,
) -> dict[str, Any]:
    report = load_json(report_path)
    return evaluate_single_report(report, doe_csv_path)


def evaluate_single_report(
    report: dict[str, Any],
    doe_csv_path: str | Path = DEFAULT_DOE_CSV,
) -> dict[str, Any]:
    report_type = _detect_report_type(report)
    doe_rows = _load_doe_rows(doe_csv_path)
    if report_type == "strategy":
        full_factorial_count = _full_factorial_count(report, doe_rows)
        planned_count = _number_at(report, "exploration_plan.planned_calculation_count")
        details = {
            "information_extraction": _score_information_extraction(report),
            "constraint_formulation": _score_constraint_formulation(report),
            "tool_selection": _score_tool_names(_tool_names(report.get("planned_tools", []))),
            "report_requirements": _score_strategy_report_requirements(report),
        }
        scores = {
            "information_extraction": details["information_extraction"]["score"],
            "constraint_formulation": details["constraint_formulation"]["score"],
            "tool_selection": details["tool_selection"]["score"],
            "exploration_strategy": _safe_ratio(full_factorial_count - planned_count, full_factorial_count),
            "report_requirements": details["report_requirements"]["score"],
        }
        return {
            "schema_version": "1.0",
            "report_type": "strategy",
            "scores": _with_mean(scores),
            "counts": {
                "full_factorial_count": full_factorial_count,
                "planned_calculation_count": planned_count,
                "doe_candidate_count": len(doe_rows),
            },
            "details": details,
        }

    full_factorial_count = float(len(doe_rows))
    planned_count = _number_at(report, "planned_vs_actual_summary.planned_calculation_count")
    actual_count = _number_at(report, "actual_calculation_count")
    details = {
        "tool_selection": _score_tool_names(_tool_names(report.get("used_tools", []))),
        "report_requirements": _score_result_report_requirements(report),
        "dr_explanation": _score_dr_explanation(report),
        "optimization": _score_optimization(report, doe_rows),
    }
    scores = {
        "tool_selection": details["tool_selection"]["score"],
        "report_requirements": details["report_requirements"]["score"],
        "dr_explanation": details["dr_explanation"]["score"],
        "optimization": details["optimization"]["score"],
        "plan_vs_actual": _plan_vs_actual_score(planned_count, actual_count),
        "calculation_count": _safe_ratio(full_factorial_count - abs(full_factorial_count - actual_count), full_factorial_count),
    }
    return {
        "schema_version": "1.0",
        "report_type": "result",
        "scores": _with_mean(scores),
        "counts": {
            "full_factorial_count": full_factorial_count,
            "planned_calculation_count": planned_count,
            "actual_calculation_count": actual_count,
            "doe_candidate_count": len(doe_rows),
        },
        "details": details,
    }


def evaluate_reports(
    strategy_report: dict[str, Any],
    result_report: dict[str, Any],
    doe_csv_path: str | Path = DEFAULT_DOE_CSV,
) -> dict[str, Any]:
    doe_rows = _load_doe_rows(doe_csv_path)
    full_factorial_count = _full_factorial_count(strategy_report, doe_rows)
    planned_count = _number_at(strategy_report, "exploration_plan.planned_calculation_count")
    actual_count = _number_at(result_report, "actual_calculation_count")

    details = {
        "information_extraction": _score_information_extraction(strategy_report),
        "constraint_formulation": _score_constraint_formulation(strategy_report),
        "tool_selection": _score_tool_selection(strategy_report, result_report),
        "report_requirements": _score_report_requirements(strategy_report, result_report),
        "dr_explanation": _score_dr_explanation(result_report),
        "optimization": _score_optimization(result_report, doe_rows),
    }

    scores = {
        "information_extraction": details["information_extraction"]["score"],
        "constraint_formulation": details["constraint_formulation"]["score"],
        "tool_selection": details["tool_selection"]["score"],
        "exploration_strategy": _safe_ratio(full_factorial_count - planned_count, full_factorial_count),
        "report_requirements": details["report_requirements"]["score"],
        "dr_explanation": details["dr_explanation"]["score"],
        "optimization": details["optimization"]["score"],
        "plan_vs_actual": _plan_vs_actual_score(planned_count, actual_count),
        "calculation_count": _safe_ratio(full_factorial_count - abs(full_factorial_count - actual_count), full_factorial_count),
    }
    scores = _with_mean(scores)

    return {
        "schema_version": "1.0",
        "scores": scores,
        "counts": {
            "full_factorial_count": full_factorial_count,
            "planned_calculation_count": planned_count,
            "actual_calculation_count": actual_count,
            "doe_candidate_count": len(doe_rows),
        },
        "details": details,
    }


def _score_information_extraction(strategy_report: dict[str, Any]) -> dict[str, Any]:
    items = strategy_report.get("extracted_information", [])
    if not isinstance(items, list):
        items = []
    matched: list[str] = []
    for canonical_id, expected in REQUIRED_EXTRACTIONS.items():
        if any(_matches_expected_item(item, expected) for item in items if isinstance(item, dict)):
            matched.append(canonical_id)

    unnecessary = [
        _item_id(item)
        for item in items
        if isinstance(item, dict) and not _matches_any(item, REQUIRED_EXTRACTIONS)
    ]
    score = _safe_ratio(len(matched) - len(unnecessary), len(REQUIRED_EXTRACTIONS))
    return {
        "score": score,
        "required_count": len(REQUIRED_EXTRACTIONS),
        "correct_count": len(matched),
        "unnecessary_count": len(unnecessary),
        "matched": matched,
        "missing": sorted(set(REQUIRED_EXTRACTIONS) - set(matched)),
        "unnecessary": unnecessary,
    }


def _score_constraint_formulation(strategy_report: dict[str, Any]) -> dict[str, Any]:
    items = strategy_report.get("constraint_formulation", [])
    if not isinstance(items, list):
        items = []
    matched: list[str] = []
    for canonical_id, expected in REQUIRED_CONSTRAINTS.items():
        if any(_matches_expected_constraint(item, expected) for item in items if isinstance(item, dict)):
            matched.append(canonical_id)

    unnecessary = [
        _item_id(item)
        for item in items
        if isinstance(item, dict) and not _matches_any(item, REQUIRED_CONSTRAINTS)
    ]
    score = _safe_ratio(len(matched) - len(unnecessary), len(REQUIRED_CONSTRAINTS))
    return {
        "score": score,
        "required_count": len(REQUIRED_CONSTRAINTS),
        "correct_count": len(matched),
        "wrong_added_count": len(unnecessary),
        "matched": matched,
        "missing": sorted(set(REQUIRED_CONSTRAINTS) - set(matched)),
        "wrong_added": unnecessary,
    }


def _score_tool_selection(strategy_report: dict[str, Any], result_report: dict[str, Any]) -> dict[str, Any]:
    names = _tool_names(strategy_report.get("planned_tools", []))
    names |= _tool_names(result_report.get("used_tools", []))
    return _score_tool_names(names)


def _score_tool_names(names: set[str]) -> dict[str, Any]:
    correct = sorted(names & REQUIRED_TOOLS)
    unnecessary = sorted(names - REQUIRED_TOOLS)
    score = _safe_ratio(len(correct) - len(unnecessary), len(REQUIRED_TOOLS))
    return {
        "score": score,
        "required_count": len(REQUIRED_TOOLS),
        "correct_count": len(correct),
        "unnecessary_or_misused_count": len(unnecessary),
        "matched": correct,
        "missing": sorted(REQUIRED_TOOLS - set(correct)),
        "unnecessary_or_misused": unnecessary,
    }


def _score_report_requirements(strategy_report: dict[str, Any], result_report: dict[str, Any]) -> dict[str, Any]:
    required = [f"strategy.{path}" for path in STRATEGY_REPORT_PATHS]
    required += [f"result.{path}" for path in RESULT_REPORT_PATHS]
    satisfied = [
        f"strategy.{path}" for path in STRATEGY_REPORT_PATHS if _has_value(strategy_report, path)
    ]
    satisfied += [
        f"result.{path}" for path in RESULT_REPORT_PATHS if _has_value(result_report, path)
    ]
    forbidden_score_fields = _score_field_paths(strategy_report, "strategy") + _score_field_paths(result_report, "result")
    score = _safe_ratio(len(satisfied) - len(forbidden_score_fields), len(required))
    return {
        "score": score,
        "required_count": len(required),
        "satisfied_count": len(satisfied),
        "unnecessary_or_contradictory_count": len(forbidden_score_fields),
        "satisfied": satisfied,
        "missing": sorted(set(required) - set(satisfied)),
        "forbidden_score_fields": forbidden_score_fields,
    }


def _score_strategy_report_requirements(strategy_report: dict[str, Any]) -> dict[str, Any]:
    required = [f"strategy.{path}" for path in STRATEGY_REPORT_PATHS]
    satisfied = [
        f"strategy.{path}" for path in STRATEGY_REPORT_PATHS if _has_value(strategy_report, path)
    ]
    forbidden_score_fields = _score_field_paths(strategy_report, "strategy")
    score = _safe_ratio(len(satisfied) - len(forbidden_score_fields), len(required))
    return {
        "score": score,
        "required_count": len(required),
        "satisfied_count": len(satisfied),
        "unnecessary_or_contradictory_count": len(forbidden_score_fields),
        "satisfied": satisfied,
        "missing": sorted(set(required) - set(satisfied)),
        "forbidden_score_fields": forbidden_score_fields,
    }


def _score_result_report_requirements(result_report: dict[str, Any]) -> dict[str, Any]:
    required = [f"result.{path}" for path in RESULT_REPORT_PATHS]
    satisfied = [
        f"result.{path}" for path in RESULT_REPORT_PATHS if _has_value(result_report, path)
    ]
    forbidden_score_fields = _score_field_paths(result_report, "result")
    score = _safe_ratio(len(satisfied) - len(forbidden_score_fields), len(required))
    return {
        "score": score,
        "required_count": len(required),
        "satisfied_count": len(satisfied),
        "unnecessary_or_contradictory_count": len(forbidden_score_fields),
        "satisfied": satisfied,
        "missing": sorted(set(required) - set(satisfied)),
        "forbidden_score_fields": forbidden_score_fields,
    }


def _score_dr_explanation(result_report: dict[str, Any]) -> dict[str, Any]:
    satisfied = [path for path in DR_EXPLANATION_PATHS if _has_value(result_report, path)]
    forbidden_score_fields = _score_field_paths(result_report, "result")
    score = _safe_ratio(len(satisfied) - len(forbidden_score_fields), len(DR_EXPLANATION_PATHS))
    return {
        "score": score,
        "required_count": len(DR_EXPLANATION_PATHS),
        "satisfied_count": len(satisfied),
        "unnecessary_or_contradictory_count": len(forbidden_score_fields),
        "satisfied": satisfied,
        "missing": sorted(set(DR_EXPLANATION_PATHS) - set(satisfied)),
        "forbidden_score_fields": forbidden_score_fields,
    }


def _score_optimization(result_report: dict[str, Any], doe_rows: list[dict[str, Any]]) -> dict[str, Any]:
    design = result_report.get("adopted_design", {})
    row = _find_doe_row_for_design(design, doe_rows)
    pass_rows = [r for r in doe_rows if r.get("status") == "PASS"]
    if row is None:
        return {
            "score": -1.0,
            "status": "NOT_FOUND",
            "reason": "adopted_design_not_found_in_doe",
            "feasible_count": len(pass_rows),
            "rank": None,
        }
    if row.get("status") != "PASS":
        return {
            "score": -1.0,
            "status": row.get("status"),
            "reason": row.get("ng_reasons", "adopted_design_is_not_feasible"),
            "feasible_count": len(pass_rows),
            "rank": None,
            "matched_row": _compact_row(row),
        }
    if len(pass_rows) <= 1:
        rank = 1
        score = 1.0
    else:
        rank = pass_rows.index(row) + 1
        score = (len(pass_rows) - rank) / (len(pass_rows) - 1)
    return {
        "score": score,
        "status": "PASS",
        "feasible_count": len(pass_rows),
        "rank": rank,
        "matched_row": _compact_row(row),
    }


def _load_doe_rows(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            parsed = dict(row)
            parsed["length_mm"] = _to_float(row.get("length_mm"))
            parsed["cost_jpy"] = _to_float(row.get("cost_jpy"))
            parsed["dimensions"] = json.loads(row.get("dimensions", "{}"))
            rows.append(parsed)
    return rows


def _detect_report_type(report: dict[str, Any]) -> str:
    report_type = str(report.get("report_type", "")).strip().lower()
    if report_type in {"strategy", "result"}:
        return report_type
    if "extracted_information" in report or "exploration_plan" in report:
        return "strategy"
    if "adopted_design" in report or "constraint_results" in report:
        return "result"
    raise ValueError("report_type must be 'strategy' or 'result'")


def _find_doe_row_for_design(design: Any, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not isinstance(design, dict):
        return None
    material = design.get("material")
    length = _to_float(design.get("length_mm", design.get("length")))
    section = design.get("section", {})
    if isinstance(section, dict):
        shape = section.get("shape", design.get("shape"))
        dimensions = section.get("dimensions", design.get("dimensions", {}))
    else:
        shape = design.get("shape")
        dimensions = design.get("dimensions", {})
    for row in rows:
        if row.get("material") != material:
            continue
        if row.get("shape") != shape:
            continue
        if not _close(row.get("length_mm"), length):
            continue
        if _dimensions_equal(row.get("dimensions", {}), dimensions):
            return row
    return None


def _compact_row(row: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "material",
        "shape",
        "length_mm",
        "dimensions",
        "cost_jpy",
        "bending_stress_mpa",
        "twist_angle_deg",
        "thermal_displacement_mm",
        "max_accelerance",
        "first_bending_hz",
        "ng_reasons",
    ]
    return {k: row.get(k) for k in keys if k in row}


def _matches_expected_item(item: dict[str, Any], expected: dict[str, Any]) -> bool:
    item_id = _item_id(item)
    if item_id not in expected["aliases"]:
        return False
    if "value" in expected and not _value_matches(item.get("value"), expected["value"]):
        return False
    sources = _sources(item)
    expected_sources = expected.get("sources", set())
    if expected_sources and sources and not (sources & expected_sources):
        return False
    return True


def _matches_expected_constraint(item: dict[str, Any], expected: dict[str, Any]) -> bool:
    item_id = _item_id(item)
    if item_id not in expected["aliases"]:
        return False
    criterion = str(item.get("criterion", item.get("operator", ""))).strip().lower()
    if expected.get("criterion") and criterion not in expected["criterion"]:
        return False
    if "value" in expected and not _value_matches(item.get("value", item.get("limit")), expected["value"]):
        return False
    return True


def _matches_any(item: dict[str, Any], expected_items: dict[str, dict[str, Any]]) -> bool:
    item_id = _item_id(item)
    return any(item_id in expected["aliases"] for expected in expected_items.values())


def _item_id(item: dict[str, Any]) -> str:
    return str(item.get("id", item.get("name", ""))).strip()


def _sources(item: dict[str, Any]) -> set[str]:
    raw = item.get("source_ids", item.get("sources", item.get("source_id", item.get("source", []))))
    if isinstance(raw, str):
        return {raw}
    if isinstance(raw, list):
        return {str(v) for v in raw}
    return set()


def _tool_names(items: Any) -> set[str]:
    if not isinstance(items, list):
        return set()
    names: set[str] = set()
    for item in items:
        if isinstance(item, str):
            names.add(item)
        elif isinstance(item, dict):
            name = item.get("name", item.get("tool"))
            if name:
                names.add(str(name))
    return names


def _value_matches(value: Any, expected: Any) -> bool:
    if isinstance(expected, list):
        if not isinstance(value, list) or len(value) != len(expected):
            return False
        return all(_close(_to_float(v), e, rel=1e-3, abs_tol=1e-3) for v, e in zip(value, expected))
    if isinstance(expected, float):
        return _close(_to_float(value), expected, rel=1e-3, abs_tol=1e-3)
    return value == expected


def _dimensions_equal(left: Any, right: Any) -> bool:
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    if set(left) != set(right):
        return False
    return all(_close(_to_float(left[k]), _to_float(right[k])) for k in left)


def _has_value(data: dict[str, Any], path: str) -> bool:
    value: Any = data
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return False
        value = value[part]
    return not _is_placeholder(value)


def _is_placeholder(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value == "" or value.startswith("TODO")
    if isinstance(value, list):
        return not value or all(_is_placeholder(item) for item in value)
    if isinstance(value, dict):
        return not value or all(_is_placeholder(item) for item in value.values())
    return False


def _number_at(data: dict[str, Any], path: str) -> float:
    value: Any = data
    for part in path.split("."):
        if not isinstance(value, dict):
            return 0.0
        value = value.get(part)
    return _to_float(value)


def _full_factorial_count(strategy_report: dict[str, Any], doe_rows: list[dict[str, Any]]) -> float:
    reported = _number_at(strategy_report, "exploration_plan.full_factorial_count")
    if reported > 0:
        return reported
    return float(len(doe_rows))


def _plan_vs_actual_score(planned_count: float, actual_count: float) -> float:
    if planned_count <= 0:
        return 0.0
    return 1.0 - abs(actual_count - planned_count) / planned_count


def _with_mean(scores: dict[str, float]) -> dict[str, float]:
    scores = dict(scores)
    scores["unweighted_mean"] = sum(scores.values()) / len(scores) if scores else 0.0
    return scores


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _score_field_paths(value: Any, prefix: str) -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{prefix}.{key}"
            lowered = str(key).lower()
            if lowered in {"score", "scores"} or lowered.endswith("_score") or lowered.endswith("_scores"):
                paths.append(child_path)
            paths.extend(_score_field_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(_score_field_paths(child, f"{prefix}[{index}]"))
    return paths


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _close(left: Any, right: Any, rel: float = 1e-6, abs_tol: float = 1e-6) -> bool:
    return math.isclose(_to_float(left), _to_float(right), rel_tol=rel, abs_tol=abs_tol)
