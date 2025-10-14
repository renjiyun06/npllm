# Section 2: Compilation Specification

**Goal**: Define the input, output, and rules for compiling semantic call sites into prompts.

**Input (compile_task XML)**:

```xml
<compile_task>
  <task_id>[Unique identifier]</task_id>
  <code_context>
[Complete code context per Section 1]
  </code_context>
  <semantic_call_site>
    <location>
      <line_number>[Where the call occurs]</line_number>
      <method_name>[Invoked name]</method_name>
    </location>
    <parameter_spec>
      <positional>
        <param position="[0-indexed]" type="[type]" />
        ...
      </positional>
      <keyword>
        <param name="[name]" type="[type]" />
        ...
      </keyword>
    </parameter_spec>
    <return_specification>
      <type>[Python type]</type>
      <json_schema>
[JSON Schema of the return value]
      </json_schema>
    </return_specification>
  </semantic_call_site>
</compile_task>
```

**Key input elements**:

- task_id: use exactly in all delimiters
- code_context: complete surrounding code per Section 1
- location: where the call occurs
- parameter_spec: positional and keyword parameters
- return_specification: return type and JSON Schema

**Output (delimiter format)**:

```
=={task_id}==SYSTEM_PROMPT==
[system prompt]
=={task_id}==END_SYSTEM_PROMPT==
=={task_id}==USER_PROMPT==
[user prompt template]
=={task_id}==END_USER_PROMPT==
=={task_id}==NOTES==
[optional compilation notes]
=={task_id}==END_NOTES==
```

**Components**:

- System Prompt: define role, task, execution guidelines; include output schema/format; never expose code symbols.
- User Prompt Template: state the specific invocation, include all parameters via the placeholder protocol, present data readably; include schema only if context-dependent.
- Notes (optional): key decisions, directives handled, assumptions, schema choices.

**Output schema**:

- Refinement: use as-is when precise; refine if generic/incomplete using call-site context, domain, and comments; document in NOTES.
- Placement: default in SYSTEM_PROMPT; put in USER_PROMPT if it must be read with specific input; mixing narrative vs formal schema is allowed.
- Presentation: full JSON Schema (preferred), or natural language for simple cases; may add an example.

**Critical output requirements**:

1) Exact task_id in all delimiters
2) Delimiter format with `==` on both sides
3) SYSTEM_PROMPT and USER_PROMPT required; NOTES optional
4) Include output schema appropriately in SYSTEM or USER prompt
5) Do not output XML (only delimiters)

**Directives** (compiler extensions in comments):

- Syntax:

```python
# @compile: [instruction]
```

```python
# @compile{
#   [instruction line 1]
#   [instruction line 2]
# }@
```

- Semantics: constrain structure, style, format, length, or tone.
- Processing: identify, prioritize compliance, apply precisely, never expose, document in NOTES.

**Parameter Reference Protocol** (strict placeholder syntax):

- Basic format: `{{placeholder_name}}`
- Naming: positional → `{{argN}}`; keyword → exact name (e.g., `{{user_request}}`).
- Field access: dot notation for structured types (e.g., `{{request.user_id}}`).
- Collections: reference whole collections (e.g., `{{items}}`), never subscripts.
- Prohibited: subscripts (`{{items[0]}}`), method calls, expressions, conditionals.

**Presentation strategy**:

- Direct user input:

```
The user said: {{user_message}}
```

- Simple scalars:

```
User ID: {{user_id}}
Session Token: {{session_token}}
```

- Collections:

```
Conversation history:
{{message_history}}
```

- Complex objects (use structure, e.g., XML or labeled fields):

```
<request>
  <user_id>{{request.user_id}}</user_id>
  <message>{{request.message}}</message>
</request>
```

Guiding principle: prioritize readability for the runtime LLM.