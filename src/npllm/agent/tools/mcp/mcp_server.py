from typing import Dict, Any, Union, Optional, List
from dataclasses import dataclass

from mcp import StdioServerParameters, ClientSession, ListToolsResult
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult

@dataclass
class Tool:
    name: str
    description: Optional[str]
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]]

@dataclass
class ToolResult:
    content: Any
    is_error: bool

class McpServer:
    def __init__(
        self, 
        server_name: str, 
        server_parameters: Union[StdioServerParameters, Dict[str, Any]]
    ):
        self._server_name = server_name
        self._server_parameters = self._parse_server_parameters(server_parameters)
        self._client_session: ClientSession = None
        self._stdio_context = None

    def _parse_server_parameters(
        self, 
        server_parameters: Union[StdioServerParameters, Dict[str, Any]]
    ) -> StdioServerParameters:
        if isinstance(server_parameters, StdioServerParameters):
            return server_parameters
        return StdioServerParameters(**server_parameters)

    async def connect(self):
        stdio_context = stdio_client(self._server_parameters)
        read_stream, write_stream = await stdio_context.__aenter__()
        client_session = ClientSession(read_stream, write_stream)
        await client_session.__aenter__()
        await client_session.initialize()
        self._client_session = client_session
        self._stdio_context = stdio_context

    async def disconnect(self):
        await self._client_session.__aexit__(None, None, None)
        await self._stdio_context.__aexit__(None, None, None)

    async def list_tools(self) -> List[Tool]:
        list_tool_result: ListToolsResult = await self._client_session.list_tools()
        tools: List[Tool] = []
        for tool in list_tool_result.tools:
            tools.append(Tool(
                name = tool.name,
                description = tool.description,
                input_schema = tool.inputSchema,
                output_schema = tool.outputSchema
            ))
        return tools

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        call_tool_result: CallToolResult = await self._client_session.call_tool(name, arguments)
        return ToolResult(content=call_tool_result.content, is_error=call_tool_result.isError)

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.disconnect()