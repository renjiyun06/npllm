from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any

from npllm.core.ai import AI
from npllm.core.code_context_provider import ClassCodeContextProvider
from npllm.core.executors.llm_executor.llm_executor import LLMExecutor
from npllm.agent.tools.mcp.mcp_server import McpServer, Tool, ToolResult

import logging

logger = logging.getLogger(__name__)

@dataclass
class ToolCall:
    tool_name: str
    args: Dict[str, Any]

class GitHubTrendingAgent(AI):
    def __init__(self, cdp_endpoint: str):
        AI.__init__(
            self, 
            call_site_executor=LLMExecutor(code_context_provider=ClassCodeContextProvider())
        )

        self._playwright_toolset = McpServer(
            server_name="playwright",
            server_parameters={
                "command": "npx",
                "args": ["@playwright/mcp@latest", "--cdp-endpoint", cdp_endpoint]
            }
        )

    async def query(self, q: str) -> str:
        async with self._playwright_toolset as toolset:
            tools: List[Tool] = await toolset.list_tools()
            session: List[Tuple[ToolCall, ToolResult]] = []
            tool_results: List[ToolResult] = []
            while True:
                tool_call: Optional[ToolCall] = await self.choose_tool(q, session, tools)
                if tool_call is None:
                    break
                tool_result: ToolResult = await toolset.call_tool(tool_call.tool_name, tool_call.args)
                tool_results.append(tool_result)
                session.append((tool_call, tool_result))

            return await self.reason(q, tool_results)