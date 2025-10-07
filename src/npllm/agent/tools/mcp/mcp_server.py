from typing import Dict, Any, Union, Optional, List
from dataclasses import dataclass

from mcp import StdioServerParameters, ClientSession
from mcp.client.stdio import stdio_client

@dataclass
class Tool:
    name: str
    description: Optional[str]=None
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]]=None

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

    async def _connect(self):
        stdio_context = stdio_client(self._server_parameters)
        read_stream, write_stream = await stdio_context.__aenter__()
        client_session = ClientSession(read_stream, write_stream)
        await client_session.__aenter__()
        await client_session.initialize()
        self._client_session = client_session
        self._stdio_context = stdio_context

    async def _disconnect(self):
        await self._client_session.__aexit__(None, None, None)
        await self._stdio_context.__aexit__(None, None, None)

    async def list_tools(self) -> List[Tool]:
        return [Tool(**tool) for tool in await self._client_session.list_tools()]

    async def call_tool(self, name: str, arguments: Dict[str, Any]):
        return await self._client_session.call_tool(name, arguments)

    async def __aenter__(self):
        await self._connect()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._disconnect()