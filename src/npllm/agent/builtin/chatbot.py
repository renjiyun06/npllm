from typing import Any, Dict, List, Tuple, Optional

from npllm.core.ai import AI
from npllm.core.executors.agent_executor import ExecutableAgent, Task, OutputSpec
from npllm.agent.tools.mcp.mcp_server import McpServer, Tool, ToolResult

import logging

logger = logging.getLogger(__name__)

class ChatBot(AI, ExecutableAgent):
    def __init__(self):
        AI.__init__(self)
        ExecutableAgent.__init__(self, "chatbot")

    async def execute(self, task: Task, output_spec: OutputSpec) -> Any:
        pass