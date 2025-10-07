from npllm.core.llm import LLM
from npllm.agent.tools.mcp.mcp_server import McpServer

import logging

logger = logging.getLogger(__name__)

class WebContentExtractor(LLM):
    def __init__(self):
        LLM.__init__(self)