import time
from importlib import resources
from typing import List, Any, Dict
import xml.etree.ElementTree as ET
from pathlib import Path
import re

from litellm import acompletion, ModelResponse

from npllm.core.call_site import CallSite, CallSiteIdentifier
from npllm.core.code_context import CodeContext
from npllm.core.compiler import Compiler, CompilationResult, SystemPromptTemplate, UserPromptTemplate

import logging

logger = logging.getLogger(__name__)

class DefaultSystemPromptTemplate(SystemPromptTemplate):
    def __init__(self, role_and_context: str, task_description: str, guidelines: str):
        self.role_and_context = role_and_context
        self.task_description = task_description
        self.guidelines = guidelines
    
    def format(self, output_json_schema: str, args: List[Any], kwargs: Dict[str, Any]) -> str:
        return f"""
<system_prompt>
<role_and_context>
{self.role_and_context.strip()}
</role_and_context>
<task_description>
{self.task_description.strip()}
</task_description>
<guidelines>
{self.guidelines.strip()}
</guidelines>
<output_format>
The output should be formatted as a JSON instance that conforms to the JSON schema below.

As an example, for the schema {{"properties": {{"foo": {{"title": "Foo", "description": "a list of strings", "type": "array", "items": {{"type": "string"}}}}}}, "required": ["foo"]}}
the object {{"foo": ["bar", "baz"]}} is a well-formatted instance of the schema. The object {{"properties": {{"foo": ["bar", "baz"]}}}} is not well-formatted.

Here is the output schema:
```
{output_json_schema}
```

CRITICAL REQUIREMENTS:
- Output ONLY raw JSON, no explanations or extra text before/after
- Do NOT use ```json code blocks or any markdown formatting
- Do NOT add newlines or indentation - output compact single-line JSON
- All required fields must be present
- Data types must exactly match the schema
- String values MUST be enclosed in double quotes "", numeric values must NOT have quotes
- All special characters in strings MUST be properly escaped: \\" for quotes, \\\\ for backslashes, \\n for newlines, \\t for tabs
</output_format>
</system_prompt>
""".strip()

    def to_xml(self) -> str:
        return f"""
<system_prompt>
<role_and_context>
{self.role_and_context}
</role_and_context>
<task_description>
{self.task_description}
</task_description>
<guidelines>
{self.guidelines}
</guidelines>
</system_prompt>
""".strip()

class DefaultUserPromptTemplate(UserPromptTemplate):
    def __init__(self, template: str):
        self._template = template
    
    def to_xml(self) -> str:
        return f"""
<user_prompt_template>
{self._template}
</user_prompt_template>
""".strip()

    def format(self, args: List[Any], kwargs: Dict[str, Any]) -> str:
        template = self._template
        placeholders = re.findall(r"{{[^}]+}}", template)
        for original_placeholder in placeholders:
            placeholder = original_placeholder
            placeholder = placeholder.replace("{{", "").replace("}}", "")
            
            root_obj = None
            dot_chain = []
            if placeholder.startswith("arg"):
                placeholder = placeholder[len("arg"):]
                position_index = int(placeholder.split(".")[0])
                root_obj = args[position_index]
                dot_chain = placeholder.split(".")[1:]
            else:
                root_obj = kwargs[placeholder.split(".")[0]]
                dot_chain = placeholder.split(".")[1:]

            value = root_obj
            for field in dot_chain:
                value = getattr(value, field)

            formatted_value: List[str] = []
            if isinstance(value, (list, tuple)):
                for item in value:
                    formatted_value.append(str(item))
            elif isinstance(value, dict):
                for key, item in value.items():
                    formatted_value.append(f"{key}: {str(item)}")
            else:
                formatted_value.append(str(value))

            template = template.replace(original_placeholder, "\n".join(formatted_value))

        return template.strip()

class CompilationNotes:
    def __init__(self, notes: str):
        self.notes = notes

    def to_xml(self) -> str:
        return f"""
<compilation_notes>
{self.notes}
</compilation_notes>
""".strip()

class DefaultCompilationResult:
    tag_compilation_result = "compilation_result"
    tag_system_prompt = "system_prompt"
    tag_role_and_context = "role_and_context"
    tag_task_description = "task_description"
    tag_guidelines = "guidelines"
    tag_user_prompt_template = "user_prompt_template"
    tag_compilation_notes = "compilation_notes"

    @classmethod
    def from_llm_response(cls, response: ModelResponse) -> 'DefaultCompilationResult':
        response_content = response.choices[0].message.content.strip()
        logger.debug(f"Raw response content from compile-time LLM: {response_content}")
        if response_content.startswith("```xml"):
            response_content = response_content[len("```xml"):-len("```")]

        root = ET.fromstring(response_content)
        return cls._parse(root)

    @classmethod
    def from_cache_file(cls, cache_file: Path) -> 'DefaultCompilationResult':
        with open(cache_file, "r", encoding='utf-8') as f:
            root = ET.fromstring(f.read())
        
        return cls._parse(root)

    @classmethod
    def _get_xml_node_complete_content(cls, node: ET.Element, target_node_tag: str) -> str:
        target_node = node.find(target_node_tag)
        if target_node is None:
            raise RuntimeError(f"Cannot find target node {target_node_tag} in the node {node}")
        
        result = ET.tostring(target_node, encoding='utf-8').decode('utf-8').strip()
        return result.replace(f"<{target_node_tag}>", "").replace(f"</{target_node_tag}>", "").strip()

    @classmethod
    def _parse(cls, root: ET.Element) -> 'DefaultCompilationResult':
        system_prompt_node = root.find(cls.tag_system_prompt)
        role_and_context = cls._get_xml_node_complete_content(system_prompt_node, cls.tag_role_and_context)
        task_description=cls._get_xml_node_complete_content(system_prompt_node, cls.tag_task_description)
        guidelines=cls._get_xml_node_complete_content(system_prompt_node, cls.tag_guidelines)
        system_prompt_template = DefaultSystemPromptTemplate(
            role_and_context=role_and_context,
            task_description=task_description,
            guidelines=guidelines
        )
        user_prompt_template = cls._get_xml_node_complete_content(root, cls.tag_user_prompt_template)
        user_prompt_template = DefaultUserPromptTemplate(user_prompt_template)
        compilation_notes = cls._get_xml_node_complete_content(root, cls.tag_compilation_notes)
        compilation_notes = CompilationNotes(compilation_notes)
        create_time = float(root.get("create_time")) if root.get("create_time") else time.time()
        return cls(system_prompt_template, user_prompt_template, compilation_notes, create_time)

    def __init__(
        self, 
        system_prompt_template: DefaultSystemPromptTemplate, 
        user_prompt_template: DefaultUserPromptTemplate, 
        compilation_notes: CompilationNotes,
        create_time: float
    ):
        self.system_prompt_template = system_prompt_template
        self.user_prompt_template = user_prompt_template
        self.compilation_notes = compilation_notes
        self.create_time = create_time

    def to_xml(self) -> str:
        return f"""
<compilation_result create_time="{self.create_time}">
{self.system_prompt_template.to_xml()}
{self.user_prompt_template.to_xml()}
{self.compilation_notes.to_xml()}
</compilation_result>
""".strip()

class CompilationTask:
    def __init__(self, call_site: CallSite, code_context: CodeContext):
        self._call_site = call_site
        self._code_context = code_context

    def __str__(self) -> str:
        code_context, relative_line_number = self._code_context.get_code_context(self._call_site, self._call_site)
        positional_parameters = []
        keyword_parameters = []
        for arg_name, arg_type in self._call_site.args_types:
            if isinstance(arg_name, int):
                positional_parameters.append(f"""<param position="{arg_name}" type="{arg_type}" />""")
            else:
                keyword_parameters.append(f"""<param name="{arg_name}" type="{arg_type}" />""")
        
        return f"""
<compile_task>
<code_context>
{code_context}
</code_context>
<call_site>
<line_number>{relative_line_number}</line_number>
<method_name>{self._call_site.identifier.method_name}</method_name>
</call_site>
<positional_parameters>
{'\n'.join(positional_parameters)}
</positional_parameters>
<keyword_parameters>
{'\n'.join(keyword_parameters)}
</keyword_parameters>
<return_type>{self._call_site.return_type}</return_type>
</compile_task>
""".strip()

class DefaultCompiler(Compiler):
    cache_dir = Path("~/.npllm/compilers/default/caches").expanduser()

    def __init__(self, model: str):
        self._model = model
        self._system_prompt_path = (
            resources.files('npllm.core.compilers.default') / 
            "system_prompt.md"
        )
        self._system_prompt = self._load_prompt()
        self._compilation_result_cache: Dict[CallSiteIdentifier, DefaultCompilationResult] = self._load_cache()

    def _load_cache(self) -> Dict[CallSiteIdentifier, DefaultCompilationResult]:
        DefaultCompiler.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_files = DefaultCompiler.cache_dir.glob("*.xml")
        cache = {}
        for cache_file in cache_files:
            call_site_identifier = CallSiteIdentifier.from_cache_filename(cache_file.name)
            cache[call_site_identifier] = DefaultCompilationResult.from_cache_file(cache_file)
        return cache

    def _load_prompt(self):
        return self._system_prompt_path.read_text(encoding='utf-8')

    def _save_cache(self, call_site: CallSite, compilation_result: DefaultCompilationResult):
        logger.info(f"Save compilation result to cache for call site {call_site}")
        self._compilation_result_cache[call_site.identifier] = compilation_result
        DefaultCompiler.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_filename = call_site.identifier.to_cache_filename()
        path = DefaultCompiler.cache_dir / cache_filename
        with open(path, "w", encoding='utf-8') as f:
            f.write(compilation_result.to_xml())

    async def compile(self, call_site: CallSite, code_context: CodeContext) -> CompilationResult:
        if call_site.identifier in self._compilation_result_cache:
            compilation_result = self._compilation_result_cache[call_site.identifier]
            dependent_modules = call_site.dependent_modules
            for dependent_module in dependent_modules:
                module_filename = dependent_module.__file__
                module_last_modified_time = Path(module_filename).stat().st_mtime
                if module_last_modified_time > compilation_result.create_time:
                    logger.info(f"Dependent module {dependent_module} has been modified, need to recompile")
                    break
            else:
                logger.info(f"No dependent modules have been modified, return cached compilation result for {call_site}")
                return compilation_result

        logger.info(f"Compile the call site {call_site} with model {self._model}")
        task = CompilationTask(call_site, code_context)
        logger.debug(f"Compilation task: {task}")
        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": f"{task}"}
        ]

        try:
            response = await acompletion(
                model=self._model,
                messages=messages
            )
            compilation_result = DefaultCompilationResult.from_llm_response(response)
            logger.info(f"Successfully compiled the call site {call_site}")
            self._save_cache(call_site, compilation_result)
            return CompilationResult(
                system_prompt_template=compilation_result.system_prompt_template,
                user_prompt_template=compilation_result.user_prompt_template
            )
        except Exception as e:
            # TODO here we need a retry mechanism
            raise e