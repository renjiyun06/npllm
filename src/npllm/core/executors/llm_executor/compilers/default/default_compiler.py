import time
from importlib import resources
from typing import List, Any, Dict
import xml.etree.ElementTree as ET
from pathlib import Path
import re

from litellm import acompletion, ModelResponse

from npllm.core.call_site import CallSite, CallSiteIdentifier
from npllm.core.code_context import CodeContext
from npllm.core.executors.llm_executor.compiler import Compiler, CompilationResult, SystemPromptTemplate, UserPromptTemplate

import logging

logger = logging.getLogger(__name__)

class DefaultSystemPromptTemplate(SystemPromptTemplate):
    def __init__(self, node: ET.Element):
        self._node = node
    
    def format(self, args: List[Any], kwargs: Dict[str, Any]) -> str:
        role_and_context = self._node.find(DefaultCompilationResult.tag_role_and_context).text.strip()
        task_description = self._node.find(DefaultCompilationResult.tag_task_description).text.strip()
        guidelines = self._node.find(DefaultCompilationResult.tag_guidelines).text.strip()
        output = self._node.find(DefaultCompilationResult.tag_output)
        output_json_schema = output.find(DefaultCompilationResult.tag_output_json_schema).text.strip()
        format_guidance = output.find(DefaultCompilationResult.tag_format_guidance).text.strip()
        return f"""
<role_and_context>
{role_and_context}
</role_and_context>
<task_description>
{task_description}
</task_description>
<guidelines>
{guidelines}
</guidelines>
<output>
{output_json_schema}
</output_json_schema>
<format_guidance>
{format_guidance}
</format_guidance>
</output>
""".strip()
        

class DefaultUserPromptTemplate(UserPromptTemplate):
    def __init__(self, node: ET.Element):
        self._node = node

    def format(self, args: List[Any], kwargs: Dict[str, Any]) -> str:
        template = self._node.text
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
            if isinstance(value, list):
                for item in value:
                    formatted_value.append(str(item))
            else:
                formatted_value.append(str(value))

            template = template.replace(original_placeholder, "\n".join(formatted_value))

        return template.strip()

class CompilationNotes:
    def __init__(self, node: ET.Element):
        self._node = node

class DefaultCompilationResult:
    tag_compilation_result = "compilation_result"
    tag_system_prompt = "system_prompt"
    tag_role_and_context = "role_and_context"
    tag_task_description = "task_description"
    tag_guidelines = "guidelines"
    tag_output = "output"
    tag_output_json_schema = "output_json_schema"
    tag_format_guidance = "format_guidance"
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
    def _parse(cls, root: ET.Element) -> 'DefaultCompilationResult':
        ET.indent(root, space="  ", level=0)
        system_prompt_node = root.find(cls.tag_system_prompt)
        system_prompt_template = DefaultSystemPromptTemplate(system_prompt_node)

        user_prompt_template_node = root.find(cls.tag_user_prompt_template)
        user_prompt_template = DefaultUserPromptTemplate(user_prompt_template_node)

        compilation_notes_node = root.find(cls.tag_compilation_notes)
        compilation_notes = CompilationNotes(compilation_notes_node)

        create_time = float(root.get("create_time")) if root.get("create_time") else time.time()
        return cls(root, system_prompt_template, user_prompt_template, compilation_notes, create_time)

    def __init__(
        self,
        root: ET.Element,
        system_prompt_template: DefaultSystemPromptTemplate, 
        user_prompt_template: DefaultUserPromptTemplate, 
        compilation_notes: CompilationNotes,
        create_time: float
    ):
        self.root = root
        self.system_prompt_template = system_prompt_template
        self.user_prompt_template = user_prompt_template
        self.compilation_notes = compilation_notes
        self.create_time = create_time

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
    <location>
      <line_number>{relative_line_number}</line_number>
      <method_name>{self._call_site.identifier.method_name}</method_name>
    </location>

    <parameter_spec>
      <positional>
      {'\n'.join(positional_parameters)}
      </positional>
      <keyword>
      {'\n'.join(keyword_parameters)}
      </keyword>
    </parameter_spec>
    
    <return_specification>
      <type>{self._call_site.return_type}</type>
      <json_schema>
{self._call_site.return_type.json_schema()}
      </json_schema>
    </return_specification>
  </call_site>
</compile_task>
""".strip()

class DefaultCompiler(Compiler):
    cache_dir = Path("~/.npllm/compilers/default/caches").expanduser()

    def __init__(self, model: str):
        self._model = model
        self._system_prompt_path = (
            resources.files('npllm.core.executors.llm_executor.compilers.default') / 
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
            f.write(ET.tostring(compilation_result.root, encoding='utf-8').decode('utf-8'))

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