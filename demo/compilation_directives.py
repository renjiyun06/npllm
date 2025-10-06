from npllm.core.llm import LLM

llm = LLM()
# @compile: use Chinese to write the prompt
# Be concise, reply with one sentence
result: str = llm.reason('Where does "hello world" come from?')  
print(result)