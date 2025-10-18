import npllm

import logging

logging.basicConfig(level=logging.WARNING, format='%(name)s - %(levelname)s - %(message)s')

npllm_logger = logging.getLogger('npllm')
npllm_logger.setLevel(logging.DEBUG)

# Be concise, reply with one sentence
result: str = reason('Where does "hello world" come from?')  
print(result)