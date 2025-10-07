from npllm.core.ai import AI

import logging

logging.basicConfig(level=logging.WARNING, format='%(name)s - %(levelname)s - %(message)s')

npllm_logger = logging.getLogger('npllm')
npllm_logger.setLevel(logging.DEBUG)

ai = AI()
# @compile: use Chinese to write the prompt
# Be concise, reply with one sentence
result: str = ai.reason('Where does "hello world" come from?')  
print(result)