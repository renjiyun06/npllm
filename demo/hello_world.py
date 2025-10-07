from npllm.core.ai import AI

ai = AI()
# Be concise, reply with one sentence
result: str = ai.reason('Where does "hello world" come from?')  
print(result)