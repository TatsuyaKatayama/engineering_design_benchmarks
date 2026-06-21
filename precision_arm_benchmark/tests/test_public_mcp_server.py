import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "public"))

from armbench_public.public_mcp_server import (  # noqa: E402
    PUBLIC_MCP_TOOL_NAMES,
    call_public_tool,
    handle_jsonrpc,
    list_public_tools,
)
from armbench_public.public_tools import PUBLIC_MCP_TOOL_NAMES as PUBLIC_TOOL_NAMES  # noqa: E402

EXPECTED_PUBLIC_TOOLS = set(PUBLIC_TOOL_NAMES)


class PublicMcpServerTest(unittest.TestCase):
    def test_public_mcp_tool_names_match_public_manifest_names(self):
        self.assertEqual(set(PUBLIC_MCP_TOOL_NAMES), EXPECTED_PUBLIC_TOOLS)
        self.assertEqual({tool["name"] for tool in list_public_tools()}, EXPECTED_PUBLIC_TOOLS)

    def test_jsonrpc_tools_list_uses_expected_tool_names(self):
        response = handle_jsonrpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(names, EXPECTED_PUBLIC_TOOLS)

    def test_calculate_section_tool_call(self):
        result = call_public_tool(
            "calculate_section",
            {
                "section": {
                    "shape": "solid_round",
                    "dimensions": {"diameter_mm": 20.0},
                }
            },
        )

        self.assertAlmostEqual(result["area_mm2"], 314.1592653589793)

    def test_jsonrpc_tool_call_returns_text_json(self):
        response = handle_jsonrpc(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "get_generation_specs",
                    "arguments": {"generation": "gen2"},
                },
            }
        )

        content = response["result"]["content"][0]
        parsed = json.loads(content["text"])
        self.assertEqual(parsed["generation"], "gen2")
        self.assertFalse(response["result"]["isError"])


if __name__ == "__main__":
    unittest.main()
