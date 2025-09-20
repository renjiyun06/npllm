# npllm: 面向大型语言模型的自然编程

**npllm** 是一个前沿的 Python 库, 它将大型语言模型 (LLM) 无缝集成到您的代码中. 它将基于字符串, 充满繁琐提示工程的 LLM 交互, 转变为一种原生的, 类型安全的, 具备上下文感知能力的编程体验.

借助 `npllm`, 您可以像调用本地函数一样调用 LLM, 并使用您早已熟悉并喜爱的工具来定义其输出结构: **Python 的类型提示**.

## 传统 LLM 集成的问题

在传统应用中集成 LLM 通常涉及:

1. 手动编写详尽的文本提示 (Prompt).
2. 将上下文和示例注入到提示字符串中.
3. 调用 LLM 的 API.
4. 接收一个原始字符串或松散结构的 JSON 响应.
5. 解析, 验证这个响应, 并将其反序列化为可用的 Python 对象.
6. 每当需求变更时, 重复整个过程.

这个过程不仅脆弱, 容易出错, 而且将"提示逻辑"与"应用逻辑"分离开来.

## `npllm` 的解决方案: 代码即提示

`npllm` 彻底改变了这一模式. 不再是您为模型编写提示, 而是模型来适应您的代码.

```python
from dataclasses import dataclass
from npllm.core.llm import LLM

# 1. 定义您期望的数据结构
@dataclass
class UserProfile:
    name: str
    age: int
    is_active: bool
    interests: list[str]

# 2. 创建一个 LLM 实例
llm = LLM()

# 3. 使用类型提示作为返回类型, 调用一个方法并描述您的需求
async def generate_user() -> UserProfile:
    # 框架会自动理解它需要返回一个 UserProfile 对象
    return await llm.generate_a_user_profile(
        description="一个喜欢科幻小说和古典音乐的用户. "
    )

# 最终结果是一个清晰, 经过验证且可直接使用的 Python 对象! 
user = await generate_user()
print(user)
# 预期输出: UserProfile(name='...', age=..., is_active=..., interests=['科幻小说', '古典音乐', ...])
```

## 核心特性

✨ **零提示, 上下文感知**: 告别手动编写提示! `npllm` 会自动分析调用上下文, 包括函数源码, 文档字符串和方法参数, 为 LLM 即时生成一个精确的提示.

🔒 **类型安全的输出**: 您的类型提示 (例如 `-> MyDataClass`) 成为一种契约. `npllm` 会指示 LLM 返回一个与您的 `dataclass` 或类型定义相匹配的 JSON 对象, 然后安全地解析, 验证响应, 并将其转换为可直接使用的 Python 对象. 从此告别手动解析和验证.

🧠 **自动 `dataclass` 和类型解析**: 框架足够智能, 它会检查您的类型提示, 并自动查找所有相关的 `dataclass` 定义和类型别名——即使是复杂的, 嵌套的或递归的定义. 然后, 它会将这些类型的源代码包含在给 LLM 的上下文中, 确保模型能完全理解期望的输出结构.

🚀 **输入自然语言, 输出结构化数据**: 无缝地将自然语言需求转换为结构化的, 类型安全的 Python 对象. 这对于数据提取, 配置生成或将指令编译为具体操作等任务是理想的选择.

🎭 **基于角色的特化**: 通过简单地继承 `npllm.LLM` 并使用文档字符串 (docstring) 来分配一个高级“角色”, 您可以创建特化的 LLM “代理”. 这可以引导 LLM 在特定任务上的行为, 让您能够构建强大的, 可复用的工具, 如编译器, 聊天机器人或数据分析器.

🐍 **完美兼容 Jupyter/Notebook**: 从设计之初就考虑了在 Jupyter Notebook 等交互式环境中的使用体验, 让实验和原型开发变得快速而直观.

## 工作原理

`npllm` 通过一个精密的多步骤过程来实现其功能, 而这一切对用户来说都是透明的:

1. **调用**: 您调用 `LLM` 实例上的一个动态方法 (例如 `await llm.reason(...)`).
2. **调用点分析**: 框架检查“调用点”, 从您的函数类型提示中确定**期望的返回类型** (例如 `-> UserProfile`).
3. **上下文 AST 解析**: 它解析您代码的抽象语法树 (AST), 以查找所有相关上下文. 这包括 `UserProfile` 数据类的源码以及它所依赖的任何其他类型.
4. **动态提示构建**: 它构建一个详细的系统级提示, 指示 LLM 其角色, 提供完整的代码上下文, 并根据发现的类型指定所需的 JSON 输出结构.
5. **LLM 执行与验证**: 它调用 LLM, 接收 JSON 响应, 并根据预期结构进行严格验证.
6. **类型转换**: 它将经过验证的 JSON 对象转换为一个纯净的 Python 对象 (例如 `UserProfile` 的一个实例) 并返回.

## 安装指南

首先, 使用 pip 安装 `npllm`:

```bash
pip install npllm
```

您还需要配置您的 LLM 提供商. `npllm` 在底层使用 `litellm`, 因此它支持广泛的提供商 (OpenAI, Gemini, Anthropic 等). 请根据 `litellm` 的文档设置所需的环境变量.

例如, 对于 OpenAI:

```bash
export OPENAI_API_KEY="your-api-key"
```

## 高级示例: 构建一个由 LLM 驱动的编译器

`npllm` 的强大之处在复杂任务中最为明显. `demo/llm_compiler.py` 示例展示了如何创建一个“编译器”, 该编译器能将一种简单的命令式编程语言翻译成结构化的抽象语法树 (AST), 而这一切都由 LLM 驱动.

`LLMCompiler` 类使用其文档字符串来设定角色, 而 `compile` 方法则使用 `Program` 数据类作为其返回类型提示. 框架会自动将整个 AST 的定义提供给 LLM, 使其能够将一个代码字符串转换为一个深度嵌套的 Python 对象.

这展示了该框架处理高度复杂, 递归的数据结构以及执行高级的"自然语言到代码"转换的能力.