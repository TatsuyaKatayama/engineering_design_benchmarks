from __future__ import annotations

import json
import sys
from typing import Any, Callable

from .geometry import section_from_dict
from .knowledge import get_generation_specs, search_failure_knowledge
from .public_tools import PUBLIC_MCP_TOOL_NAMES
from .solvers import (
    calculate_accelerance,
    calculate_bending,
    calculate_cost,
    calculate_section,
    calculate_thermal_displacement,
    calculate_torsion,
    design_from_dict,
    run_doe,
)


def call_public_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name not in TOOL_HANDLERS:
        raise ValueError(f"unknown public MCP tool: {name}")
    return TOOL_HANDLERS[name](arguments)


def list_public_tools() -> list[dict[str, Any]]:
    return [TOOL_DEFINITIONS[name] for name in PUBLIC_MCP_TOOL_NAMES]


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        request = json.loads(line)
        response = handle_jsonrpc(request)
        if response is not None:
            print(json.dumps(response, ensure_ascii=False), flush=True)


def handle_jsonrpc(request: dict[str, Any]) -> dict[str, Any] | None:
    request_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "precision-arm-public-tools", "version": "1.0.0"},
            }
        elif method == "tools/list":
            result = {"tools": list_public_tools()}
        elif method == "tools/call":
            tool_name = params["name"]
            arguments = params.get("arguments", {})
            tool_result = call_public_tool(tool_name, arguments)
            result = {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(tool_result, ensure_ascii=False, sort_keys=True),
                    }
                ],
                "isError": False,
            }
        else:
            raise ValueError(f"unsupported method: {method}")
        if request_id is None:
            return None
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except Exception as exc:
        if request_id is None:
            return None
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32000, "message": str(exc)},
        }


def _tool_calculate_section(arguments: dict[str, Any]) -> dict[str, Any]:
    section_data = arguments.get("section", arguments)
    return calculate_section(section_from_dict(section_data))


def _tool_calculate_bending(arguments: dict[str, Any]) -> dict[str, Any]:
    return calculate_bending(design_from_dict(_design_data(arguments)))


def _tool_calculate_torsion(arguments: dict[str, Any]) -> dict[str, Any]:
    return calculate_torsion(design_from_dict(_design_data(arguments)))


def _tool_calculate_cost(arguments: dict[str, Any]) -> dict[str, Any]:
    return calculate_cost(design_from_dict(_design_data(arguments)))


def _tool_calculate_thermal_displacement(arguments: dict[str, Any]) -> dict[str, Any]:
    return calculate_thermal_displacement(design_from_dict(_design_data(arguments)))


def _tool_calculate_accelerance(arguments: dict[str, Any]) -> dict[str, Any]:
    return calculate_accelerance(design_from_dict(_design_data(arguments)))


def _tool_run_doe(arguments: dict[str, Any]) -> dict[str, Any]:
    return run_doe(arguments.get("doe", arguments))


def _tool_search_failure_knowledge(arguments: dict[str, Any]) -> dict[str, Any]:
    return search_failure_knowledge(
        query=str(arguments["query"]),
        top_k=int(arguments.get("top_k", 5)),
    )


def _tool_get_generation_specs(arguments: dict[str, Any]) -> dict[str, Any]:
    generation = arguments.get("generation")
    return get_generation_specs(None if generation in (None, "") else str(generation))


def _design_data(arguments: dict[str, Any]) -> dict[str, Any]:
    data = arguments.get("design", arguments)
    if not isinstance(data, dict):
        raise ValueError("design arguments must be an object")
    return data


def _schema_tool(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required or [],
            "additionalProperties": True,
        },
    }


SECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "shape": {"type": "string"},
        "dimensions": {"type": "object", "additionalProperties": {"type": "number"}},
    },
    "required": ["shape", "dimensions"],
    "additionalProperties": False,
}

DESIGN_SCHEMA = {
    "type": "object",
    "properties": {
        "material": {"type": "string"},
        "length_mm": {"type": "number"},
        "section": SECTION_SCHEMA,
        "static_tip_force_n": {"type": "number"},
        "dynamic_tip_mass_g": {"type": "number"},
        "tip_torque_nmm": {"type": "number"},
        "damping_ratio": {"type": "number"},
        "temperature_delta_c": {"type": "number"},
        "frequency_min_hz": {"type": "number"},
        "frequency_max_hz": {"type": "number"},
        "frequency_step_hz": {"type": "number"},
    },
    "required": [
        "material",
        "length_mm",
        "section",
        "static_tip_force_n",
        "dynamic_tip_mass_g",
    ],
    "additionalProperties": True,
}

TOOL_DEFINITIONS = {
    "calculate_section": _schema_tool(
        "calculate_section",
        "断面積、断面二次モーメント、断面係数、ねじり定数を計算する。",
        {"section": SECTION_SCHEMA},
        ["section"],
    ),
    "calculate_bending": _schema_tool(
        "calculate_bending",
        "先端外乱荷重による曲げ変形量、最大曲げ応力を計算する。",
        {"design": DESIGN_SCHEMA},
        ["design"],
    ),
    "calculate_torsion": _schema_tool(
        "calculate_torsion",
        "先端ねじりモーメントによるねじれ角、最大せん断応力を計算する。",
        {"design": DESIGN_SCHEMA},
        ["design"],
    ),
    "calculate_cost": _schema_tool(
        "calculate_cost",
        "材料コストと参考アーム質量を計算する。",
        {"design": DESIGN_SCHEMA},
        ["design"],
    ),
    "calculate_thermal_displacement": _schema_tool(
        "calculate_thermal_displacement",
        "温度変化による先端熱変位量を計算する。",
        {"design": DESIGN_SCHEMA},
        ["design"],
    ),
    "calculate_accelerance": _schema_tool(
        "calculate_accelerance",
        "周波数範囲内の先端アクセレランス最大値、ピーク周波数、1次曲げ固有値を計算する。",
        {"design": DESIGN_SCHEMA},
        ["design"],
    ),
    "run_doe": _schema_tool(
        "run_doe",
        "指定水準のDOE候補を生成し、各候補に順問題計算結果を付与する。最適案は選定しない。",
        {
            "levels": {"type": "integer"},
            "fixed": {"type": "object"},
            "materials": {"type": "array", "items": {"type": "string"}},
            "length_mm": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2},
            "sections": {"type": "array", "items": {"type": "object"}},
        },
        ["materials", "length_mm", "sections"],
    ),
    "search_failure_knowledge": _schema_tool(
        "search_failure_knowledge",
        "疑似RAGとして過去トラ知識を決定論的に検索する。",
        {"query": {"type": "string"}, "top_k": {"type": "integer"}},
        ["query"],
    ),
    "get_generation_specs": _schema_tool(
        "get_generation_specs",
        "第1・第2・第3世代および開発条件の構造化仕様を取得する。",
        {"generation": {"type": "string"}},
        [],
    ),
}

TOOL_HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "calculate_section": _tool_calculate_section,
    "calculate_bending": _tool_calculate_bending,
    "calculate_torsion": _tool_calculate_torsion,
    "calculate_cost": _tool_calculate_cost,
    "calculate_thermal_displacement": _tool_calculate_thermal_displacement,
    "calculate_accelerance": _tool_calculate_accelerance,
    "run_doe": _tool_run_doe,
    "search_failure_knowledge": _tool_search_failure_knowledge,
    "get_generation_specs": _tool_get_generation_specs,
}

if set(TOOL_DEFINITIONS) != set(PUBLIC_MCP_TOOL_NAMES):
    raise RuntimeError("public MCP tool definitions do not match public tool names")
if set(TOOL_HANDLERS) != set(PUBLIC_MCP_TOOL_NAMES):
    raise RuntimeError("public MCP tool handlers do not match public tool names")


if __name__ == "__main__":
    main()
