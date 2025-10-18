from npllm.core.ai import AI
from npllm.core.execute_engines.default.default_execution_engine import DefaultExecutionEngine

import logging

logging.basicConfig(level=logging.WARNING, format='%(name)s - %(levelname)s - %(message)s')

npllm_logger = logging.getLogger('npllm')
npllm_logger.setLevel(logging.DEBUG)

ai = AI(semantic_execute_engine=DefaultExecutionEngine())
# @compile: use Chinese to write the prompt
# Be concise, reply with one sentence
result: str = ai.reason('Where does "hello world" come from?')  
print(result)