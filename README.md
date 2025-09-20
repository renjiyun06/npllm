# npllm: No Prompt Large Language Model

**npllm** is a cutting-edge Python library that seamlessly integrates Large Language Models (LLMs) into your code. It transforms LLM interactions from a string-based, prompt-engineering hassle into a native, type-safe, and context-aware programming experience.

With `npllm`, you make LLM calls as if they were regular Python functions, and you define their output structure using the tools you already know and love: **Python's type hints**.

## The Problem with Traditional LLM Integration

Traditionally, using an LLM in an application involves:

1. Manually writing detailed text prompts.
2. Injecting context and examples into the prompt string.
3. Making an API call to the LLM.
4. Receiving a raw string or a loosely-structured JSON response.
5. Parsing, validating, and deserializing this response into usable Python objects.
6. Repeating this entire process every time a requirement changes.

This process is brittle, error-prone, and separates the "prompt logic" from the "application logic."

## The `npllm` Solution: Code as the Prompt

`npllm` flips the script. Instead of you writing prompts for the model, the model adapts to your code.

```python
from dataclasses import dataclass
from npllm.core.llm import LLM

# 1. Define your desired data structure
@dataclass
class UserProfile:
    name: str
    age: int
    is_active: bool
    interests: list[str]

# 2. Create an LLM instance
llm = LLM()

# 3. Call a method with your requirements, using a type hint for the return value
async def generate_user() -> UserProfile:
    # The framework automatically understands that it needs to return a UserProfile object
    return await llm.generate_a_user_profile(
        description="A user who is a fan of science fiction and classical music."
    )

# The result is a clean, validated, and ready-to-use Python object!
user = await generate_user()
print(user)
# Expected Output: UserProfile(name='...', age=..., is_active=..., interests=['science fiction', 'classical music', ...])
```

## Core Features

✨ **Zero-Prompt, Context-Aware Calls**: Stop writing prompts! `npllm` automatically analyzes the calling context, including function source code, docstrings, and method arguments, to generate a precise, on-the-fly prompt for the LLM.

🔒 **Type-Safe Outputs**: Your type hints (`-> MyDataClass`) become a contract. `npllm` instructs the LLM to return a JSON object matching your `dataclass` or type definition, then safely parses and validates the response, converting it into a ready-to-use Python object. No more manual parsing or validation.

🧠 **Automatic `dataclass` and Type Resolution**: The framework is intelligent. It inspects your type hints and automatically finds all related `dataclass` definitions and type aliases—even complex, nested, or recursive ones. It then includes their source code in the LLM's context, ensuring the model fully understands the desired output structure.

🚀 **Natural Language in, Structured Data out**: Seamlessly convert natural language requirements into structured, type-safe Python objects. This is ideal for tasks like data extraction, configuration generation, or compiling instructions into actions.

🎭 **Role-Based Specialization**: Create specialized LLM "agents" by simply subclassing `npllm.LLM` and using a docstring to assign a high-level "role." This guides the LLM's behavior for specific tasks, allowing you to build powerful, reusable tools like compilers, chatbots, or data analyzers.

🐍 **Jupyter/Notebook Friendly**: Designed from the ground up to work flawlessly in interactive environments like Jupyter Notebooks, making experimentation and prototyping fast and intuitive.

## How It Works

`npllm` performs its magic through a sophisticated, multi-step process that remains completely hidden from the user:

1. **Invocation**: You call a dynamic method on an `LLM` instance (e.g., `await llm.reason(...)`).
2. **Call Site Analysis**: The framework inspects the "call site" to determine the **expected return type** from your function's type hint (e.g., `-> UserProfile`).
3. **Contextual AST Parsing**: It parses your code's Abstract Syntax Tree (AST) to find all relevant context. This includes the source code of the `UserProfile` dataclass and any other types it depends on.
4. **Dynamic Prompt Construction**: It constructs a detailed, system-level prompt that instructs the LLM on its role, provides the full code context, and specifies the required JSON output structure based on the types it discovered.
5. **LLM Execution & Validation**: It calls the LLM, receives the JSON response, and rigorously validates it against the expected structure.
6. **Type Conversion**: It converts the validated JSON object into a clean Python object (e.g., an instance of `UserProfile`) and returns it.

## Installation

To get started, install `npllm` using pip:

```bash
pip install npllm
```

You will also need to configure your LLM provider. `npllm` uses `litellm` under the hood, so it supports a wide range of providers (OpenAI, Gemini, Anthropic, etc.). Set the required environment variables as per the `litellm` documentation.

For example, for OpenAI:

```bash
export OPENAI_API_KEY="your-api-key"
```

## Advanced Example: Building an LLM-Powered Compiler

The power of `npllm` is most evident in complex tasks. The `demo/llm_compiler.py` example shows how to create a "compiler" that translates a simple imperative programming language into a structured AST, all powered by an LLM.

The `LLMCompiler` class uses its docstring to set its role, and the `compile` method uses the `Program` dataclass as its return type hint. The framework automatically provides the LLM with the definitions for the entire AST, enabling it to convert a code string into a deeply nested Python object.

This demonstrates the framework's ability to handle highly complex, recursive data structures and perform sophisticated natural language-to-code transformations.