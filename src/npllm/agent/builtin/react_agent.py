from npllm.core.ai import AI
from npllm.core.executors.llm_executor.llm_executor import LLMExecutor
from npllm.core.code_context_provider import FunctionCodeContextProvider

import logging

logger = logging.getLogger(__name__)

class ReactAgent(AI):
    def __init__(self, model: str="openrouter/google/gemini-2.5-flash"):
        AI.__init__(
            self, 
            call_site_executor=LLMExecutor(
                runtime_model=model, 
                code_context_provider=FunctionCodeContextProvider()
            )
        )
