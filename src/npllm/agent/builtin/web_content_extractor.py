from typing import Any, Dict, List, Tuple, Optional

from npllm.core.ai import AI
from npllm.core.executors.agent_executor import ExecutableAgent, Task, OutputSpec
from npllm.agent.tools.mcp.mcp_server import McpServer, Tool, ToolResult

import logging

logger = logging.getLogger(__name__)

class WebContentExtractor(AI, ExecutableAgent):
    def __init__(self, cdp_endpoint):
        AI.__init__(self)
        ExecutableAgent.__init__(self, "web_content_extractor")
        self._mcp_server = McpServer(
            server_name = "playwright",
            server_parameters = {
                "command": "npx",
                "args": [
                    "@playwright/mcp@latest",
                    "--cdp-endpoint", cdp_endpoint
                ]
            }
        )

    def introduce_yourself(self) -> str:
        return "A web content extractor"

    async def execute(self, task: Task, output_spec: OutputSpec) -> Any:
        async with self._mcp_server as mcp_server:
            tools: List[Tool] = await mcp_server.list_tools()
            tool_results: List[ToolResult] = []
            while True:
                tool_name_and_args: Optional[Tuple[str, Dict[str, Any]]] = await self.choose_tool(task, tool_results, tools)
                if tool_name_and_args is None:
                    break
                tool_result: ToolResult = await mcp_server.call_tool(tool_name_and_args[0], tool_name_and_args[1])
                tool_results.append(tool_result)
            
            return await self.reason(task, tool_results, output_spec)