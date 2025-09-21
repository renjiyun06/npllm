# This example copies from https://ai.pydantic.dev/#hello-world-example

from npllm.core.llm import LLM

llm = LLM()
result = llm.reason('Where does "hello world" come from?')
print(result)