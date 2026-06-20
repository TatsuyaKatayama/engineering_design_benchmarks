import json
import unittest

from armbench.evaluation import REQUIRED_TOOLS
from armbench.public_mcp_server import (
    PUBLIC_MCP_TOOL_NAMES,
    call_public_tool,
    handle_jsonrpc,
    list_public_tools,
)


class PublicMcpServerTest(unittest.TestCase):
    def test_public_mcp_tool_names_match_evaluator_expected_names(self):
        self.assertEqual(set(PUBLIC_MCP_TOOL_NAMES), REQUIRED_TOOLS)
        self.assertEqual({tool["name"] for tool in list_public_tools()}, REQUIRED_TOOLS)

    def test_jsonrpc_tools_list_uses_expected_tool_names(self):
        response = handle_jsonrpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(names, REQUIRED_TOOLS)

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
